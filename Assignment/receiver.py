import sys
import socket
import pickle

port = int(sys.argv[1])
filename = sys.argv[2]

def calc_checksum(data):
    total_sum = 0
    for i in range(0, len(data)):
        total_sum = (total_sum + data[i])%256
    return ~total_sum & 0xFFFF

class Receiver:
    def __init__(self, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))
        self.fp = open(filename, 'wb')
        self.outlog = open('Receiver_log.txt', 'w')

    def send_data(self, addr, packet):
        data = pickle.dumps(packet)
        self.socket.sendto(data, addr)

    def recv_data(self):
        data, addr = self.socket.recvfrom(8192)
        packet = pickle.loads(data)
        return packet, addr

    def wait_connection(self):
        packet, addr = self.recv_data()
        # wait sync
        if packet['sync']:
            # send sync/ack
            print('receiver received SYNC packet')
            print('receiver received SYNC packet', file=self.outlog)
            packet = {'sync':True,'ack':True,'fin':False,'seq_num':0,'ack_num':1,'checksum':0,'payload':''}
            print('receiver send SYNC/ACK packet')
            print('receiver send SYNC/ACK packet', file=self.outlog)
            self.send_data(addr, packet)
            packet, addr = self.recv_data()
            if packet['ack']:
                print('receiver received ACK packet')
                print('receiver received ACK packet', file=self.outlog)
        print('connection built ok')
        print('connection built ok', file=self.outlog)

    def wave(self, packet, addr, seq):
        print('receiver received FIN packet')
        print('receiver received FIN packet', file=self.outlog)
        sender_seq = packet['seq_num']
        print('receiver send ACK packet with ack_num', sender_seq + 1)
        print('receiver send ACK packet', file=self.outlog)
        packet = {'sync':True,'ack':True,'fin':False,'seq_num':seq,'ack_num':sender_seq + 1,'checksum':0,'payload':''}
        self.send_data(addr, packet)
        print('receiver send FIN packet')
        print('receiver send FIN packet', file=self.outlog)
        packet = {'sync':False,'ack':False,'fin':True,'seq_num':seq + 1,'ack_num':0,'checksum':0,'payload':''}
        self.send_data(addr, packet)
        packet, addr = self.recv_data()
        if packet['ack']:
            print('receiver received ACK packet')
            print('receiver received ACK packet', file=self.outlog)
            print('connection closed')
            print('connection closed', file=self.outlog)

    def do_receive(self):
        amount_of_data_received = 0
        total_segments_received = 4
        data_segments_received = 0
        segments_bit_errors = 0
        duplicate_segments_received = 0
        duplicate_acks_sent = 0

        ack_send = set()
        seq = 1
        lastByteRcv = -1
        while True:
            packet, addr = self.recv_data()
            if packet['fin']:
                # close
                self.fp.close()
                self.wave(packet, addr, seq)
                break
            # content packet
            data = packet['payload']
            checksum = packet['checksum']
            print('receiver received data packet, seq = ', packet['seq_num'])
            print('receiver received data packet, seq = ', packet['seq_num'], file=self.outlog)
            total_segments_received += 1
            data_segments_received += 1
            if checksum != calc_checksum(data):
                # data is error
                segments_bit_errors += 1
                print('data format is error')
                print('data format is error', file=self.outlog)
            elif packet['seq_num'] == lastByteRcv + 1:
                lastByteRcv = packet['seq_num'] + len(data) - 1
                amount_of_data_received = lastByteRcv
                self.fp.write(data)
            elif packet['seq_num'] < lastByteRcv + 1:
                print('receiver get the duplicate packet')
                print('receiver get the duplicate packet', file=self.outlog)
                duplicate_segments_received += 1
            packet = {'sync':False,'ack':True,'fin':False,'seq_num':seq,'ack_num':lastByteRcv + 1,'checksum':0,'payload':''}
            print('receiver send ACK packet with ack num', lastByteRcv + 1)
            print('receiver send ACK packet with ack num', lastByteRcv + 1, file=self.outlog)
            if lastByteRcv + 1 not in ack_send:
                ack_send.add(lastByteRcv + 1)
            else:
                print('receiver send the duplicate ack', file=self.outlog)
                print('receiver send the duplicate ack', file=self.outlog)
                duplicate_acks_sent += 1
            self.send_data(addr, packet)

        print('================================')
        print('================================', file=self.outlog)
        print('Amount of Data Received (bytes):', amount_of_data_received)
        print('Amount of Data Received (bytes):', amount_of_data_received, file=self.outlog)
        print('Total segments received:', total_segments_received)
        print('Total segments received:', total_segments_received, file=self.outlog)
        print('Data segments received:', data_segments_received)
        print('Data segments received:', data_segments_received, file=self.outlog)
        print('Data Segments with bit errors:', segments_bit_errors)
        print('Data Segments with bit errors:', segments_bit_errors, file=self.outlog)
        print('Duplicate data segments received:', duplicate_segments_received)
        print('Duplicate data segments received:', duplicate_segments_received, file=self.outlog)
        print('Duplicate Acks sent:', duplicate_acks_sent)
        print('Duplicate Acks sent:', duplicate_acks_sent, file=self.outlog)
        print('================================')
        print('================================', file=self.outlog)
        self.outlog.close()

if __name__ == '__main__':
    receiver = Receiver(port)
    receiver.wait_connection()
    receiver.do_receive()
