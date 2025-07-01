# skeleton.py
from gevent import socket
from gevent.pool import Pool
from gevent.server import StreamServer

from collections import namedtuple
from io import BytesIO

class CommandError(Exception):
    pass

class Disconnect(Exception):
    pass

Error = namedtuple('Error', ('message',))

class ProtocolHandler:
    def __init__(self):
        self.handlers = {
            b'+': self.handle_simple_string,
            b'-': self.handle_error,
            b':': self.handle_integer,
            b'$': self.handle_string,
            b'*': self.handle_array,
            b'%': self.handle_dict,
        }

    def handle_request(self, socket_file):
        first_byte = socket_file.read(1)
        if not first_byte:
            raise Disconnect()
        handler = self.handlers.get(first_byte)
        if not handler:
            raise CommandError('bad request')
        return handler(socket_file)

    def handle_simple_string(self, socket_file):
        line = socket_file.readline()
        return line.rstrip(b'\r\n').decode('utf-8')

    def handle_error(self, socket_file):
        line = socket_file.readline()
        return Error(line.rstrip(b'\r\n').decode('utf-8'))

    def handle_integer(self, socket_file):
        line = socket_file.readline()
        return int(line.rstrip(b'\r\n'))

    def handle_string(self, socket_file):
        length_line = socket_file.readline()
        length = int(length_line.rstrip(b'\r\n'))
        if length == -1:
            return None
        data = socket_file.read(length + 2)
        s = data[:-2]
        try:
            return s.decode('utf-8')
        except UnicodeDecodeError:
            return s

    def handle_array(self, socket_file):
        length_line = socket_file.readline()
        num = int(length_line.rstrip(b'\r\n'))
        return [self.handle_request(socket_file) for _ in range(num)]

    def handle_dict(self, socket_file):
        length_line = socket_file.readline()
        num = int(length_line.rstrip(b'\r\n'))
        items = [self.handle_request(socket_file) for _ in range(num * 2)]
        return dict(zip(items[0::2], items[1::2]))

    def write_response(self, socket_file, data):
        buf = BytesIO()
        self._write(buf, data)
        buf.seek(0)
        socket_file.write(buf.read())
        socket_file.flush()

    def _write(self, buf, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(data, (bytes, bytearray)):
            buf.write(b'$%d\r\n' % len(data))
            buf.write(data + b'\r\n')
        elif isinstance(data, int):
            buf.write(b':%d\r\n' % data)
        elif isinstance(data, Error):
            buf.write(b'-%s\r\n' % data.message.encode('utf-8'))
        elif isinstance(data, (list, tuple)):
            buf.write(b'*%d\r\n' % len(data))
            for item in data:
                self._write(buf, item)
        elif isinstance(data, dict):
            buf.write(b'%%%d\r\n' % len(data))
            for k, v in data.items():
                self._write(buf, k)
                self._write(buf, v)
        elif data is None:
            buf.write(b'$-1\r\n')
        else:
            raise CommandError(f'unrecognized type: {type(data)!r}')

class Server:
    def __init__(self, host='127.0.0.1', port=31338, max_clients=64):
        self._pool = Pool(max_clients)
        self._server = StreamServer((host, port), self.connection_handler, spawn=self._pool)
        self._protocol = ProtocolHandler()
        self._kv = {}
        self._commands = self.get_commands()

    def get_commands(self):
        return {
            'GET': self.get,
            'SET': self.set,
            'DELETE': self.delete,
            'FLUSH': self.flush,
            'MGET': self.mget,
            'MSET': self.mset,
        }

    def get_response(self, data):
        if not isinstance(data, list):
            try:
                data = data.split()
            except Exception:
                raise CommandError('Request must be list or simple string')
        if not data:
            raise CommandError('Missing command')
        cmd = data[0]
        if isinstance(cmd, (bytes, bytearray)):
            cmd = cmd.decode('utf-8')
        cmd = cmd.upper()
        if cmd not in self._commands:
            raise CommandError(f'Command not found: {cmd}')
        return self._commands[cmd](*data[1:])

    def get(self, key):
        return self._kv.get(key)

    def set(self, key, value):
        self._kv[key] = value
        return 1

    def delete(self, key):
        return 1 if self._kv.pop(key, None) is not None else 0

    def flush(self):
        count = len(self._kv)
        self._kv.clear()
        return count

    def mget(self, *keys):
        return [self._kv.get(k) for k in keys]

    def mset(self, *items):
        it = iter(items)
        count = 0
        for k in it:
            v = next(it)
            self._kv[k] = v
            count += 1
        return count

    def connection_handler(self, conn, address):
        socket_file = conn.makefile('rwb')
        while True:
            try:
                data = self._protocol.handle_request(socket_file)
            except Disconnect:
                break
            try:
                resp = self.get_response(data)
            except CommandError as e:
                resp = Error(str(e))
            self._protocol.write_response(socket_file, resp)

    def run(self):
        self._server.serve_forever()

if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()
    Server().run()