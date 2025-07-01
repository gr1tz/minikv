# MiniKV

A lightweight, Redis‑like key–value store implemented in Python 3 using Gevent for concurrency and a custom RESP‑style protocol.

## Features

* **In‐memory** store with simple operations: `GET`, `SET`, `DELETE`, `FLUSH`, `MGET`, `MSET`.
* **RESP protocol** compatible handlers for strings, integers, arrays, and dictionaries.
* **Gevent**‑driven server for high‐concurrency TCP handling.
* **Client** library to talk to the server over a socket.

## Requirements

* Python 3.6+
* gevent

Install dependencies:

```bash
pip install gevent
```

## File Structure

* **skeleton.py** — server implementation and `ProtocolHandler` for parsing/writing RESP.
* **client.py**   — `Client` class for connecting to the server and issuing commands.

## Usage

### Run the Server

```bash
python skeleton.py
```

By default, the server listens on `127.0.0.1:31338`. You can change the host/port by passing them into `Server()`.

### Use the Client

```python
from client import Client

client = Client(host='127.0.0.1', port=31338)

# Set a value
client.set('foo', 'bar')  # returns 1

# Get a value
client.get('foo')         # returns 'bar'

# Delete a key
client.delete('foo')      # returns 1 or 0

# Multi‐set / multi‐get
client.mset('a','1','b','2')     # returns number of pairs set
client.mget('a','b','c')         # returns ['1','2', None]

# Flush database
client.flush()             # returns number of keys removed, clears store
```

## RESP Protocol Details

* **Simple Strings** (`+OK\r\n`)
* **Errors**         (`-ERR message\r\n`)
* **Integers**       (`:42\r\n`)
* **Bulk Strings**   (`$5\r\nhello\r\n`)
* **Arrays**         (`*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n`)
* **Dictionaries**   (`%2\r\n` key/value pairs)

Your server and client adhere to this simplified RESP for all data exchanges.

## TODO

* Add authentication commands (`AUTH`).
* Persist data to disk.
* Implement more Redis commands (lists, sets, pub/sub).


