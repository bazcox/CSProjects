import struct
import sys

# Constants for header sizes and formats
GLOBAL_HEADER_FORMAT = '<IHHIIII'
GLOBAL_HEADER_SIZE = 24
PACKET_HEADER_SIZE = 16
ETHERNET_HEADER_SIZE = 14
IP_HEADER_MIN_SIZE = 20
TCP_HEADER_MIN_SIZE = 20

def read_pcap_file(filename):
    try:
        with open(filename, 'rb') as f:
            global_header = f.read(GLOBAL_HEADER_SIZE)
            if len(global_header) < GLOBAL_HEADER_SIZE:
                print('Error: Incomplete global header.')
                sys.exit(1)
            # Determine endianness
            magic_number = struct.unpack('I', global_header[:4])[0]
            if magic_number == 0xa1b2c3d4:
                endian = '<'  # Little endian
            elif magic_number == 0xd4c3b2a1:
                endian = '>'  # Big endian
            else:
                print('Error: Unknown magic number. Not a valid PCAP file.')
                sys.exit(1)

            return endian, f.read()
    except FileNotFoundError:
        print(f'Error: File {filename} not found.')
        sys.exit(1)

def parse_packets(endian, data):
    packets = []
    offset = 0
    first_timestamp = None

    while offset < len(data):
        if offset + PACKET_HEADER_SIZE > len(data):
            break  # Incomplete packet header

        # Parse packet header
        packet_header = data[offset:offset + PACKET_HEADER_SIZE]
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack(endian + 'IIII', packet_header)
        offset += PACKET_HEADER_SIZE

        # Parse packet data
        packet_data = data[offset:offset + incl_len]
        if len(packet_data) < incl_len:
            print('Warning: Incomplete packet data, skipping packet.')
            offset += incl_len
            continue  # Skip this packet

        offset += incl_len

        # Calculate relative timestamp
        timestamp = ts_sec + ts_usec / 1e6
        if first_timestamp is None:
            first_timestamp = timestamp
        relative_timestamp = timestamp - first_timestamp

        packets.append({
            'timestamp': relative_timestamp,
            'data': packet_data
        })

    return packets

def parse_ethernet_header(packet_data):
    if len(packet_data) < ETHERNET_HEADER_SIZE:
        return None, None
    eth_header = packet_data[:ETHERNET_HEADER_SIZE]
    eth_fields = struct.unpack('!6s6sH', eth_header)
    eth_type = eth_fields[2]
    return eth_type, packet_data[ETHERNET_HEADER_SIZE:]

def parse_ip_header(packet_data):
    if len(packet_data) < IP_HEADER_MIN_SIZE:
        return None, None, None
    version_ihl = packet_data[0]
    ihl = version_ihl & 0x0F
    ip_header_length = ihl * 4
    if len(packet_data) < ip_header_length:
        return None, None, None
    ip_header = packet_data[:ip_header_length]
    ip_fields = struct.unpack('!BBHHHBBH4s4s', ip_header[:20])
    protocol = ip_fields[6]
    src_ip = ip_fields[8]
    dst_ip = ip_fields[9]
    total_length = ip_fields[2]
    return {
        'src_ip': '.'.join(map(str, src_ip)),
        'dst_ip': '.'.join(map(str, dst_ip)),
        'header_length': ip_header_length,
        'total_length': total_length,
        'protocol': protocol
    }, packet_data[ip_header_length:], ip_header_length

def parse_tcp_header(packet_data):
    if len(packet_data) < TCP_HEADER_MIN_SIZE:
        return None, None
    tcp_header = packet_data[:TCP_HEADER_MIN_SIZE]
    tcp_fields = struct.unpack('!HHLLBBHHH', tcp_header)
    src_port = tcp_fields[0]
    dst_port = tcp_fields[1]
    seq_num = tcp_fields[2]
    ack_num = tcp_fields[3]
    offset_reserved = tcp_fields[4]
    flags = tcp_fields[5]
    window_size = tcp_fields[6]
    data_offset = (offset_reserved >> 4) * 4
    if len(packet_data) < data_offset:
        return None, None
    return {
        'src_port': src_port,
        'dst_port': dst_port,
        'seq_num': seq_num,
        'ack_num': ack_num,
        'data_offset': data_offset,
        'flags': {
            'FIN': flags & 0x01,
            'SYN': (flags & 0x02) >> 1,
            'RST': (flags & 0x04) >> 2,
            'PSH': (flags & 0x08) >> 3,
            'ACK': (flags & 0x10) >> 4,
            'URG': (flags & 0x20) >> 5
        },
        'window_size': window_size
    }, packet_data[data_offset:], data_offset

def analyze_packets(packets):
    connections = {}
    connection_count = 0

    for packet in packets:
        packet_data = packet['data']
        timestamp = packet['timestamp']

        # Parse Ethernet header
        eth_type, ip_data = parse_ethernet_header(packet_data)
        if eth_type != 0x0800:  # Only process IPv4 packets
            continue

        # Parse IP header
        ip_header, tcp_data, ip_header_length = parse_ip_header(ip_data)
        if not ip_header or ip_header['protocol'] != 6:  # Only process TCP packets
            continue

        # Parse TCP header
        tcp_header, payload, tcp_header_length = parse_tcp_header(tcp_data)
        if not tcp_header:
            continue

        # Identify connection by tuple (src_ip, src_port, dst_ip, dst_port)
        conn_tuple = (
            ip_header['src_ip'],
            tcp_header['src_port'],
            ip_header['dst_ip'],
            tcp_header['dst_port']
        )
        rev_conn_tuple = (
            ip_header['dst_ip'],
            tcp_header['dst_port'],
            ip_header['src_ip'],
            tcp_header['src_port']
        )

        # Check if connection already exists
        if conn_tuple in connections:
            conn = connections[conn_tuple]
        elif rev_conn_tuple in connections:
            conn = connections[rev_conn_tuple]
        else:
            connection_count += 1
            conn = {
                'id': connection_count,
                'packets': [],
                'src_ip': ip_header['src_ip'],
                'dst_ip': ip_header['dst_ip'],
                'src_port': tcp_header['src_port'],
                'dst_port': tcp_header['dst_port'],
                'start_time': timestamp,
                'end_time': timestamp,
                'syn_from_source': False,
                'ack_from_source': False,
                'syn_count': 0,
                'fin_count': 0,
                'rst_count': 0,
                'complete': False
            }
            connections[conn_tuple] = conn

        # Update connection end time
        if timestamp > conn['end_time']:
            conn['end_time'] = timestamp

        # Determine packet direction
        direction = 'forward' if (ip_header['src_ip'], tcp_header['src_port']) == (conn['src_ip'], conn['src_port']) else 'reverse'

        # Update connection flags
        flags = tcp_header['flags']
        if flags['SYN']:
            conn['syn_count'] += 1
            if direction == 'forward':
                conn['syn_from_source'] = True
        if flags['FIN']:
            conn['fin_count'] += 1
        if flags['RST']:
            conn['rst_count'] += 1
        if flags['ACK']:
            if direction == 'forward':
                conn['ack_from_source'] = True

        # Add packet to connection
        conn['packets'].append({
            'timestamp': timestamp,
            'ip_header': ip_header,
            'tcp_header': tcp_header,
            'payload_size': ip_header['total_length'] - ip_header['header_length'] - tcp_header['data_offset'],
            'direction': direction
        })

    # Determine connection completeness
    for conn in connections.values():
        conn['complete'] = is_connection_complete(conn)
        conn['established_before_capture'] = is_established_before_capture(conn)

    return connections

def is_connection_complete(conn):
    # A connection is complete if it has at least one FIN flag
    return conn['fin_count'] > 0

def is_established_before_capture(conn):
    # Connection is established before capture if no SYN from source but ACK from source
    return not conn['syn_from_source'] and conn['ack_from_source']

def print_connection_details(connections):
    print('\nA) Total number of connections:', len(connections))
    print('________________________________________________\n')
    print("B) Connection's details\n")

    complete_connections = []
    reset_connections = 0
    open_connections = 0
    established_before_capture = 0

    for conn_id, conn in sorted(connections.items(), key=lambda x: x[1]['id']):
        print(f'Connection {conn["id"]}:')
        print(f'Source Address: {conn["src_ip"]}')
        print(f'Destination Address: {conn["dst_ip"]}')
        print(f'Source Port: {conn["src_port"]}')
        print(f'Destination Port: {conn["dst_port"]}')

        status = f'S{conn["syn_count"]}F{conn["fin_count"]}'
        if conn['rst_count'] > 0:
            status += '/R'
            reset_connections += 1
        print(f'Status: {status}')

        if conn['complete']:
            complete_connections.append(conn)
            duration = conn['end_time'] - conn['start_time']
            print(f'Start time: {conn["start_time"]:.6f} seconds')
            print(f'End Time: {conn["end_time"]:.6f} seconds')
            print(f'Duration: {duration:.6f} seconds')

            # Calculate packet and byte counts
            fwd_packets = sum(1 for pkt in conn['packets'] if pkt['direction'] == 'forward')
            rev_packets = sum(1 for pkt in conn['packets'] if pkt['direction'] == 'reverse')
            total_packets = fwd_packets + rev_packets

            fwd_bytes = sum(pkt['payload_size'] for pkt in conn['packets'] if pkt['direction'] == 'forward')
            rev_bytes = sum(pkt['payload_size'] for pkt in conn['packets'] if pkt['direction'] == 'reverse')
            total_bytes = fwd_bytes + rev_bytes

            print(f'Number of packets sent from Source to Destination: {fwd_packets}')
            print(f'Number of packets sent from Destination to Source: {rev_packets}')
            print(f'Total number of packets: {total_packets}')
            print(f'Number of data bytes sent from Source to Destination: {fwd_bytes}')
            print(f'Number of data bytes sent from Destination to Source: {rev_bytes}')
            print(f'Total number of data bytes: {total_bytes}')
        else:
            open_connections += 1

        if conn['established_before_capture']:
            established_before_capture += 1

        print('END')
        print('++++++++++++++++++++++++++++++++')

    # Print general statistics
    print('________________________________________________\n')
    print('C) General\n')
    print(f'Total number of complete TCP connections: {len(complete_connections)}')
    print(f'Number of reset TCP connections: {reset_connections}')
    print(f'Number of TCP connections that were still open when the trace capture ended: {open_connections}')
    print(f'The number of TCP connections established before the capture started: {established_before_capture}')
    print('________________________________________________')

    # Analyze complete connections for statistics
    analyze_complete_connections(complete_connections)

def analyze_complete_connections(complete_connections):
    durations = []
    rtts = []
    packets_per_connection = []
    window_sizes = []

    for conn in complete_connections:
        duration = conn['end_time'] - conn['start_time']
        durations.append(duration)
        packets_per_connection.append(len(conn['packets']))

        # Collect window sizes
        for pkt in conn['packets']:
            window_sizes.append(pkt['tcp_header']['window_size'])

        # Calculate RTT
        s = None
        send_times = {}
        for pkt in conn['packets']:
            tcp_header = pkt['tcp_header']
            direction = pkt['direction']
            flags = tcp_header['flags']
            timestamp = pkt['timestamp']
            seq_num = tcp_header['seq_num']
            ack_num = tcp_header['ack_num']

            if flags['SYN'] and direction == 'forward' and s is None:
                s = seq_num
                send_times[s] = timestamp
            elif flags['SYN'] and flags['ACK'] and direction == 'reverse' and s is not None:
                rtt = timestamp - send_times[s]
                if rtt > 0:
                    rtts.append(rtt)
                del send_times[s]
                s = None

    # Calculate statistics
    if durations:
        min_duration = min(durations)
        mean_duration = sum(durations) / len(durations)
        max_duration = max(durations)
    else:
        min_duration = mean_duration = max_duration = 0

    if rtts:
        min_rtt = min(rtts)
        mean_rtt = sum(rtts) / len(rtts)
        max_rtt = max(rtts)
    else:
        min_rtt = mean_rtt = max_rtt = 0

    if packets_per_connection:
        min_packets = min(packets_per_connection)
        mean_packets = sum(packets_per_connection) / len(packets_per_connection)
        max_packets = max(packets_per_connection)
    else:
        min_packets = mean_packets = max_packets = 0

    if window_sizes:
        min_window = min(window_sizes)
        mean_window = sum(window_sizes) / len(window_sizes)
        max_window = max(window_sizes)
    else:
        min_window = mean_window = max_window = 0

    print('\nD) Complete TCP connections\n')
    print(f'Minimum time duration: {min_duration:.6f} seconds')
    print(f'Mean time duration: {mean_duration:.6f} seconds')
    print(f'Maximum time duration: {max_duration:.6f} seconds\n')
    print(f'Minimum RTT value: {min_rtt:.6f}')
    print(f'Mean RTT value: {mean_rtt:.6f}')
    print(f'Maximum RTT value: {max_rtt:.6f}\n')
    print(f'Minimum number of packets including both send/received: {int(min_packets)}')
    print(f'Mean number of packets including both send/received: {mean_packets:.6f}')
    print(f'Maximum number of packets including both send/received: {int(max_packets)}\n')
    print(f'Minimum receive window size including both send/received: {int(min_window)} bytes')
    print(f'Mean receive window size including both send/received: {mean_window:.6f} bytes')
    print(f'Maximum receive window size including both send/received: {int(max_window)} bytes')
    print('________________________________________________\n')

def main():
    if len(sys.argv) != 2:
        print('Usage: python tcp_analyzer.py <capture_file>')
        sys.exit(1)

    capture_file = sys.argv[1]
    endian, data = read_pcap_file(capture_file)
    packets = parse_packets(endian, data)
    connections = analyze_packets(packets)
    print_connection_details(connections)

if __name__ == '__main__':
    main()
