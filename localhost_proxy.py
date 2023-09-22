#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler,HTTPServer
import argparse, os, random, sys, requests

from socketserver import ThreadingMixIn
import threading
import json
from datetime import datetime
import queue
import threading

cache_lock = threading.Lock()

hostname = ''
# Configure credentials cache to be enabled by default
cache_mode = "store"

max_queue_size = 1000000

credentials_cache = {}
# Queue to remove expired keys
cache_keys = queue.Queue()

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
            key = headers['Authorization'] + url
            resp = None
            if cache_mode == "store":
                value = credentials_cache.get(key)
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
            if resp.status_code == 200 and cache_mode == "store":
                credentials_cache[key] = {
                    "content": resp,
                    "expiration": datetime.fromisoformat(json.loads(msg)["Expiration"][:-6])
                }
                cache_keys.put(key)
                # remove expired items every time we insert, or when queue is big enough
                # max_queue_size of 0 indicates it will not bind the queue_size
                with cache_lock:
                    while((max_queue_size > 0 and cache_keys.qsize() >= max_queue_size) or datetime.now() >= credentials_cache[cache_keys.queue[0]]["expiration"]):
                        k = cache_keys.get()
                        print("Removing from cache key", k)
                        del credentials_cache[k]
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
    args = parse_args(argv)
    hostname = args.hostname
    cache_mode = args.cache_mode
    max_queue_size = args.max_queue_size
    print('HTTP server is starting on {} port {}...'.format(args.hostname, args.port))
    server_address = ('127.0.0.1', args.port)
    httpd = ThreadedHTTPServer(server_address, ProxyHTTPRequestHandler)
    print('HTTP server is running as reverse proxy')
    httpd.serve_forever()

if __name__ == '__main__':
    main()