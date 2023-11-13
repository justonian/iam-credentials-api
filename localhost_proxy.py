#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler,HTTPServer
import argparse, sys, requests
import threading
from datetime import datetime
import queue
import threading
from socketserver import ThreadingMixIn
import json

hostname = ''
cache = None

class CacheContainer():
    def __init__(self, cache_mode, max_queue_size):
        # Configure credentials cache to be enabled by default "store"
        self.cache_mode = cache_mode
        self.max_queue_size = max_queue_size
        self.credentials_cache = {}
        self.cache_lock = threading.Lock()
        # Queue to remove expired keys
        self.cache_keys = queue.Queue()

    def get(self, key):
        return self.credentials_cache.get(key)

    def put(self, key, content):
        self.clear_cache()
        self.credentials_cache[key] = content
        self.cache_keys.put(key)

    def clear_cache(self):
        # remove expired items every time we insert, or when queue is big enough
        # max_queue_size of 0 indicates it will not bind the queue_size
        self.cache_lock.acquire()
        error = None
        try:
            while(True):
                if self.cache_keys.qsize() == 0:
                    break
                top = self.cache_keys.queue[0]
                current = self.credentials_cache.get(top)
                if current == None:
                    # We already deleted this key, so just skip from the queue
                    self.cache_keys.get()
                    continue
                # If expired or greater than the configured limit remove
                if datetime.now() >= current["expiration"] or self.max_queue_size < self.cache_keys.qsize():
                    self.cache_keys.get()
                    del self.credentials_cache[top]
                    continue
                # if there are no expired items or queue is smaller than limit break purging
                break

        except BaseException as e:
            error = e
        finally:
            self.cache_lock.release()
            if error is not None:
                raise error

def merge_two_dicts(x, y):
    return x | y

def set_header(headers):
    print("Setting host")
    print(hostname)
    headers['Host'] = hostname
    return headers

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    def do_HEAD(self):
        self.do_GET(body=False)
        return
        
    def do_GET(self, body=True):
        sent = False
        try:
            url = 'https://{}{}'.format(hostname, self.path)
            req_header = self.parse_headers()
            headers = set_header(req_header)
            # C++ sdk uses lowercase authorization, so try both
            if 'Authorization' in headers:
                key = headers['Authorization'] + url
            elif 'authorization' in headers:
                key = headers['authorization'] + url
            else:
                raise 'No authorization header found in request'
            resp = None
            if cache.cache_mode == "store":
                value = cache.get(key)
                if value is not None and datetime.now() < value["expiration"]:
                    print("Using cached credentials.")
                    resp = value["content"]
            if resp is None:
                print("Requesting credentials from API. Cached credentials not avaialble.")
                resp = requests.get(url, headers=headers, verify=False)
            sent = True

            self.send_response(resp.status_code)
            self.send_resp_headers(resp)
            msg = resp.text
            if resp.status_code == 200 and cache.cache_mode == "store":
                cache.put(key, {
                    "content": resp,
                    "expiration": datetime.fromisoformat(json.loads(msg)["Expiration"][:-6])
                })
            if body:
                self.wfile.write(msg.encode(encoding='UTF-8',errors='strict'))
 
            return
        finally:
            if not sent:
                self.send_error(404, 'Error trying to proxy')

    def do_POST(self, body=True):
        sent = False
        try:
            url = 'https://{}{}'.format(hostname, self.path)
            content_len = int(self.headers.getheader('content-length', 0))
            post_body = self.rfile.read(content_len)
            req_header = self.parse_headers()
            resp = requests.post(url, data=post_body, headers=set_header(req_header), verify=False)
            sent = True

            self.send_response(resp.status_code)
            self.send_resp_headers(resp)
            if body:
                self.wfile.write(resp.content)
            return
        finally:
            if not sent:
                self.send_error(404, 'Error trying to proxy')

    def parse_headers(self):
        req_header = {}
        print("SELF REQUEST HEADEARS")
        print(self.headers)
        for line in self.headers:
            req_header[line] = self.headers[line]
        return req_header

    def send_resp_headers(self, resp):
        respheaders = resp.headers
        print ('Response Header')
        for key in respheaders:
            if key not in ['Content-Encoding', 'Transfer-Encoding', 'content-encoding', 'transfer-encoding', 'content-length', 'Content-Length']:
                print (key, respheaders[key])
                self.send_header(key, respheaders[key])
        self.send_header('Content-Length', len(resp.content))
        self.end_headers()

def parse_args(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Proxy HTTP requests')
    parser.add_argument('--port', dest='port', type=int, default=9999,
                        help='Serve HTTP requests on specified port (default: 9999)')
    parser.add_argument('--cache_mode', dest='cache_mode', type=str, default="store",
                        help='Cache GET requests until credentials expiration')
    parser.add_argument('--max_queue_size', dest='max_queue_size', type=int, default=1000000,
                        help='Cache GET requests until credentials expiration')
    parser.add_argument('--hostname', dest='hostname', type=str, default='t7b9p81x86.execute-api.us-east-1.amazonaws.com',
                        help='Hostname to be processd (default: t7b9p81x86.execute-api.us-east-1.amazonaws.com)')
    args = parser.parse_args(argv)
    return args

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def main(argv=sys.argv[1:]):
    global hostname
    global cache_mode
    global max_queue_size
    global cache
    args = parse_args(argv)
    hostname = args.hostname
    cache_mode = args.cache_mode
    max_queue_size = args.max_queue_size
    cache = CacheContainer(cache_mode, max_queue_size)
    print('HTTP server is starting on {} port {}...'.format(args.hostname, args.port))
    server_address = ('127.0.0.1', args.port)
    httpd = ThreadedHTTPServer(server_address, ProxyHTTPRequestHandler)
    print('HTTP server is running as reverse proxy')
    httpd.serve_forever()

if __name__ == '__main__':
    main()