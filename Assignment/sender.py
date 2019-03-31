import sys
import socket
import pickle
import random
import time
from copy import deepcopy

EstimatedRTT = 500
DevRTT = 250
'''
receiver_host_ip = sys.argv[1]
receiver_port = int(sys.argv[2])
filename = sys.argv[3]
MWS = int(sys.argv[4])
MSS = int(sys.argv[5])
gamma = int(sys.argv[6])

pDrop = float(sys.argv[7])
pDuplicate = float(sys.argv[8])
pCorrupt = float(sys.argv[9])
pOrder = float(sys.argv[10])
maxOrder = int(sys.argv[11])
pDelay = float(sys.argv[12])
maxDelay = int(sys.argv[13])
seed = int(sys.argv[14])
'''
receiver_host_ip = '129.94.8.118'
receiver_port = int(5050)
filename = 'test.pdf'
MWS = int(500)
MSS = int (100)
gamma = int(0)

pDrop = float(0)
pDuplicate = float(0)
pCorrupt =float(0)
pOrder = float(0)
maxOrder = int (0)
pDelay = float(0)
maxDelay = int(0)
seed = int(1000)

timo = EstimatedRTT + gamma * DevRTT
timo *= 0.001

def calc_checksum(data):
    total_sum = 0
    for i in range(0, len(data)):
        total_sum = (total_sum + data[i])%256
    return ~total_sum & 0xFFFF

class Sender:
    def __init__(self, receiver_host_ip, receiver_port, PLD):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_host_ip = receiver_host_ip
        self.receiver_port = receiver_port
        fp = open(filename, 'rb')
        self.data = fp.read()
        fp.close()
        self.seq = -2
        self.PLD = PLD
        self.outlog = open('Sender_log.txt', 'w')

    def send_data(self, packet):
        data = pickle.dumps(packet)
        addr = (self.receiver_host_ip, self.receiver_port)
        self.socket.sendto(data, addr)

    def recv_data(self):
        try:
            data, addr = self.socket.recvfrom(8192)
            packet = pickle.loads(data)
            return packet
        except socket.timeout as e:
            return None

    def handshake(self):
        packet = {'sync':True,'ack':False,'fin':False,'seq_num':self.seq,'ack_num':0,'checksum':0,'payload':''}
        print('sender try to send SYNC packet')
        print('sender try to send SYNC packet', file=self.outlog)
        # send SYNC and wait for FIN+ACK
        self.send_data(packet)
        self.seq += 1
        packet = self.recv_data()
        if packet['sync'] and packet['ack']:
            print('sender received SYNC/ACK packet')
            print('sender received SYNC/ACK packet', file=self.outlog)
            # get FIN + ACK and send ACK
            packet = {'sync':False,'ack':True,'fin':False,'seq_num':self.seq,'ack_num':1,'checksum':0,'payload':''}
            self.send_data(packet)
            self.seq += 1
            print('sender send ACK packet')
            print('sender send ACK packet', file=self.outlog)
        print('connection built ok')
        print('connection built ok', file=self.outlog)
        self.socket.settimeout(timo)

    def wave(self, bytes):
        # send FIN and wait for ACK
        packet = {'sync':False,'ack':False,'fin':True,'seq_num':bytes,'ack_num':0,'checksum':0,'payload':''}
        print('sender try to send FIN packet with seq_num', bytes)
        print('sender try to send FIN packet', file=self.outlog)
        self.send_data(packet)
        # wait for ACK
        while True:
            packet = self.recv_data()
            if not packet['ack']:
                continue
            if packet['ack_num'] != bytes + 1:
                continue
            break
        if packet['ack'] and packet['ack_num'] == bytes + 1:
            print('sender received ACK packet')
            print('sender received ACK packet', file=self.outlog)
        packet = self.recv_data()
        if packet['fin']:
            m = packet['seq_num']
            print('sender received FIN packet')
            print('sender received FIN packet', file=self.outlog)
            packet = {'sync':False,'ack':True,'fin':False,'seq_num':bytes + 1,'ack_num': m + 1,'checksum':0,'payload':''}
            self.send_data(packet)
            print('sender send ACK packet')
            print('sender send ACK packet', file=self.outlog)
        print('connection close ok')
        print('connection close ok', file=self.outlog)

    def do_send(self):
        lastByteSent = 0
        LastByteAcked = 0
        segments_transmitted = 0
        fast_retransmission = 0
        timo_retransmission = 0
        duplicated = set()

        while LastByteAcked < len(self.data) - 1:
            while lastByteSent - LastByteAcked < MWS and lastByteSent < len(self.data) - 1:
                # can send
                canSendLen = MWS - (lastByteSent - LastByteAcked)
                send_len = min(canSendLen, MSS, len(self.data) - lastByteSent)
                content = self.data[lastByteSent:send_len + lastByteSent]
                checksum = calc_checksum(content)
                print('sender send data packet, seq_num is', lastByteSent)
                print('sender send data packet, seq_num is', lastByteSent, file=self.outlog)
                packet = {'sync':False,'ack':False,'fin':False,'seq_num':lastByteSent,'ack_num':0,'checksum':checksum,'payload':content}

                packets, reorder = PLD.restruct(packet, self.outlog)
                if len(packets) == 2:
                    self.send_data(packets[0])
                    self.send_data(packets[1])
                    lastByteSent += send_len
                    segments_transmitted += 2
                elif len(packets) == 1:
                    self.send_data(packets[0])
                    if not reorder:
                        lastByteSent += send_len
                    segments_transmitted += 1
            while lastByteSent > LastByteAcked:
                # should wait for ack
                packet = self.recv_data()
                if packet == None:
                    print('receive ACK packet timeout')
                    print('receive ACK packet timeout', file=self.outlog)
                    lastByteSent = LastByteAcked
                    timo_retransmission += 1
                    break
                elif packet['ack']:
                    print('sender received ACK packet, ack_num is', packet['ack_num'])
                    print('sender received ACK packet, ack_num is', packet['ack_num'], file=self.outlog)
                    # received the ack
                    if packet['ack_num'] == LastByteAcked:
                        fast_retransmission += 1
                    LastByteAcked = packet['ack_num']
        self.wave(LastByteAcked)
        print('================================')
        print('================================', file=self.outlog)
        print('Size of the file', len(self.data), 'bytes')
        print('Size of the file', len(self.data), 'bytes', file=self.outlog)
        print('Segments transmitted', segments_transmitted)
        print('Segments transmitted', segments_transmitted, file=self.outlog)
        print('Number of Segments handled by PLD', PLD.count)
        print('Number of Segments handled by PLD', PLD.count, file=self.outlog)
        print('Number of Segments Dropped', PLD.dropped)
        print('Number of Segments Dropped', PLD.dropped, file=self.outlog)
        print('Number of Segments Corrupted', PLD.corrupted)
        print('Number of Segments Corrupted', PLD.corrupted, file=self.outlog)
        print('Number of Segments Re-ordered', PLD.reordered)
        print('Number of Segments Re-ordered', PLD.reordered, file=self.outlog)
        print('Number of Segments Duplicated', PLD.duplicated)
        print('Number of Segments Duplicated', PLD.duplicated, file=self.outlog)
        print('Number of Segments Delayed', PLD.delayed)
        print('Number of Segments Delayed', PLD.delayed, file=self.outlog)
        print('Number of Retransmissions due to timeout', timo_retransmission)
        print('Number of Retransmissions due to timeout', timo_retransmission, file=self.outlog)
        print('Number of Fast Retransmissions', fast_retransmission // 3)
        print('Number of Fast Retransmissions', fast_retransmission // 3, file=self.outlog)
        print('Number of Duplicate Acknowledgements received', fast_retransmission)
        print('Number of Duplicate Acknowledgements received', fast_retransmission, file=self.outlog)
        print('================================')
        print('================================', file=self.outlog)
        self.outlog.close()


class PLDmodule:
    def __init__(self, pDrop, pDuplicate, pCorrupt, pOrder, maxOrder, pDelay, maxDelay, seed):
        random.seed(seed)
        self.dropped = 0
        self.corrupted = 0
        self.reordered = 0
        self.duplicated = 0
        self.delayed = 0
        self.pDrop = pDrop
        self.pDuplicate = pDuplicate
        self.pCorrupt = pCorrupt
        self.pOrder = pOrder
        self.maxOrder = maxOrder
        self.pDelay = pDelay
        self.maxDelay = maxDelay
        self.count = 0

    def restruct(self, packet, log):
        self.count += 1
        if random.random() <= self.pDrop:
            # drop the packet
            print('sender dropped packet')
            print('sender dropped packet', file=log)
            self.dropped += 1
            return [], False
        if random.random() <= self.pDuplicate:
            # forward the STP segment twice back-to-back to UDP.
            self.duplicated += 1
            print('sender duplicated packet')
            print('sender duplicated packet', file=log)
            return [packet, packet], False
        if random.random() <= self.pCorrupt:
            print('sender duplicated packet')
            print('sender duplicated packet', file=log)
            new_packet = deepcopy(packet)
            data = bytearray(new_packet['payload'])
            data[-1] = 110
            new_packet['payload'] = bytes(data)
            self.corrupted += 1
            return [new_packet], False
        if random.random() <= self.pOrder:
            print('sender Re-ordered packet')
            print('sender Re-ordered packet', file=log)
            self.reordered += 1
            new_packet = deepcopy(packet)
            new_packet['seq_num'] = 0
            return [new_packet], True
        if random.random() <= self.pDelay:
            print('sender delayed packet')
            print('sender delayed packet', file=log)
            self.delayed += 1
            time.sleep(random.randint(0,self.maxDelay) * 0.001)
            return [packet], False
        self.count -= 1
        return [packet], False

if __name__ == '__main__':
    PLD = PLDmodule(pDrop, pDuplicate, pCorrupt, pOrder, maxOrder, pDelay, maxDelay, seed)
    sender = Sender(receiver_host_ip, receiver_port, PLD)
    sender.handshake()
    sender.do_send()
