import socket
import sys
import ssl

# Create the socket and connect to the server
def create_socket(domain, encrypt):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a TCP socket
    try:
        if encrypt:
            # If HTTPS, create a secure SSL context and wrap the socket with it
            context = ssl.create_default_context()
            s = context.wrap_socket(s, server_hostname=domain)
            s.connect((domain, 443)) # Connect to port 443 for HTTPS
        else:
            s.connect((domain, 80)) # Connect to port 80 for HTTP
    except socket.error as e:
        sys.exit(f"Connection to server FAILED: {e}")
    return s

# Send the HTTP/HTTPS GET request
def send_request(sock, path, domain):
    http_request = f"GET {path} HTTP/1.1\r\nHost: {domain}\r\nConnection: Keep-Alive\r\n\r\n"
    try:
        sock.sendall(http_request.encode()) # Send the request to the server
    except socket.error as e:
        sys.exit(f"Could not send HTTP request: {e}")

# Simplified receive_response function
def receive_response(sock):
    try:
        sock.settimeout(2) # Set a timeout to prevent blocking indefinitely
        response = b"" # Initialize an empty byte string to store the response
        while True:
            try:
                part = sock.recv(4096) # Receive up to 4096 bytes at a time
                if not part:
                    break # If no more data is received, exit the loop
                response += part # Append each chunk of the response
            except socket.timeout:
                break # If no data is received within timeout, assume end of response
        return response.decode(errors='replace') # Return the full response as a decoded string
    except socket.error as e:
        sys.exit(f"Error receiving response: {e}")

# Parse the response into headers and body
def parse_response(response):
    if not response:
        sys.exit("Error: Empty response received from the server.")
    headers, _, body = response.partition("\r\n\r\n") # Split the headers and body
    header_lines = headers.splitlines() # Split headers into individual lines
    if len(header_lines) == 0:
        sys.exit("Error: No headers found in the response.")  # Handle missing headers
    status_line = header_lines[0] # The first line of headers contains the HTTP status
    # Collect cookie headers in a case-insensitive manner
    cookies = [line for line in header_lines if line.lower().startswith("set-cookie:")]
    return status_line, cookies, body, headers # Return parsed components

# Handle redirection by extracting the new location
def handle_redirect(headers):
    print("--- Redirecting ---\n")
    for line in headers.splitlines():
        if line.lower().startswith("location:"):
            return line.split(":", 1)[1].strip() # Return the redirect location
    return None  # No redirect location found

# Detect if HTTP/2 is supported
def detect_http2_support(domain):
    try:
        # Create a temporary socket with ALPN protocols 'h2' and 'http/1.1'
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()
        context.set_alpn_protocols(['h2', 'http/1.1'])
        wrapped_sock = context.wrap_socket(temp_sock, server_hostname=domain)
        wrapped_sock.connect((domain, 443)) # Connect to the server on port 443 (HTTPS)
        selected_protocol = wrapped_sock.selected_alpn_protocol() # Get the negotiated protocol
        wrapped_sock.close()
        return selected_protocol == 'h2'
    except Exception:
        return False

# Extract cookie details
def extract_cookie_details(cookies):
    cookie_list = []
    for cookie in cookies:
        parts = cookie.split(";")
        # Remove "Set-Cookie:" from the beginning of the header line in a case-insensitive manner
        cookie_header = parts[0]
        if cookie_header.lower().startswith("set-cookie:"):
            cookie_header = cookie_header[len("Set-Cookie:"):].strip()
        # Extract the cookie name
        cookie_name = cookie_header.split("=", 1)[0].strip()
        cookie_domain = None
        cookie_expires = None
        for part in parts:
            if "domain=" in part.lower():
                cookie_domain = part.split("=", 1)[1].strip() # Extract the domain if present
            if "expires=" in part.lower():
                cookie_expires = part.split("=", 1)[1].strip() # Extract expiration date if present
        cookie_list.append({"name": cookie_name, "domain": cookie_domain, "expires": cookie_expires})
    return cookie_list

# Check if the site is password-protected
def check_password_protection(status_line):
    return "401 Unauthorized" in status_line

# Handle the URL parsing, path extraction, and protocol determination
def parse_url(url):
    encrypt = False
    if url.startswith("http://"):
        url = url[7:] # Strip "http://"
    elif url.startswith("https://"):
        url = url[8:] # Strip "https://"
        encrypt = True # Use HTTPS for secure connections
    else:
        encrypt = True # Default to HTTPS if no protocol is specified
    if "/" in url:
        domain, path = url.split("/", 1)  # Split domain and path
        path = "/" + path # Add leading slash to the path
    else:
        domain = url
        path = "/" # Default to root path if no path is specified
    return domain, path, encrypt # Return the parsed components

# Handle a single HTTP request/response cycle
def handle_request(domain, path, encrypt):
    sock = create_socket(domain, encrypt) # Create a socket based on HTTP/HTTPS
    send_request(sock, path, domain) # Send the GET request
    response = receive_response(sock) # Receive the server's response
    sock.close() # Close the socket if not reusing it
    status_line, cookies, body, headers = parse_response(response) # Parse the response
    return status_line, cookies, body, headers # Return parsed data

# Main function to manage the flow
def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 WebTester.py <domain>") # Ensure a URL argument is passed

    url = sys.argv[1]
    domain, path, encrypt = parse_url(url) # Parse the URL into its components

    # Detect HTTP/2 support
    supports_http2 = False
    if encrypt:
        supports_http2 = detect_http2_support(domain)

    redirects = 0
    max_redirects = 3 # Maximum number of redirects allowed

    while True:
        print("---Request begin---")
        print(f"GET {path} HTTP/1.1\r\nHost: {domain}\r\nConnection: Keep-Alive\r\n")
        print("---Request end---")
        print("HTTP request sent, awaiting response...\n")

        # Handle the HTTP request and response
        status_line, cookies, body, headers = handle_request(domain, path, encrypt)

        # Handle redirection if necessary (limit to max_redirects)
        if "HTTP/1.0 302" in status_line or "HTTP/1.1 302" in status_line or "HTTP/1.1 301" in status_line:
            redirects += 1
            if redirects > max_redirects:
                print("--- Max Number of Redirects Reached ---")
                break
            location = handle_redirect(headers) # Get the redirect location
            if location:
                domain, path, encrypt = parse_url(location) # Parse the new URL from the redirect
                continue
            else:
                break # No Location header found; cannot redirect
        else:
            break # No redirection; proceed

    # Print header and body *OPTIONAL*
    print("--- Response header ---")
    print(headers)
    print("\n--- Response body ---")
    print(f"{body[:500]}\n") # Print the first 500 characters of the body

    # Extract cookie details
    cookie_details = extract_cookie_details(cookies)
    password_protected = check_password_protection(status_line)

    # Print the final results (website, HTTP/2 support, cookies, password protection) *MANDATORY*
    print(f"website: {domain}")
    print(f"1. Supports http2: {'yes' if supports_http2 else 'no'}")
    print(f"2. List of Cookies:")
    for cookie in cookie_details:
        name = cookie["name"]
        domain_name = f"domain name: {cookie['domain']}" if cookie["domain"] else ""
        expires_time = f"expires time: {cookie['expires']}" if cookie["expires"] else ""
        # Clean up formatting by removing unnecessary commas and spaces
        details = ', '.join(filter(None, [f"cookie name: {name}", expires_time, domain_name]))
        print(details)
    print(f"3. Password-protected: {'yes' if password_protected else 'no'}")

if __name__ == '__main__':
    main()
