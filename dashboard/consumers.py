import asyncio
import fcntl
import json
import os
import pty
import shutil
import signal
import struct
import termios

from channels.generic.websocket import AsyncWebsocketConsumer


class TerminalConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self._read_task = None

        try:
            self.master_fd, self.slave_fd = pty.openpty()
            self._set_winsize(24, 80)

            shell = shutil.which('bash') or '/bin/sh'
            self.process = await asyncio.create_subprocess_exec(
                shell, '--login',
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                env={**os.environ, 'TERM': 'xterm-256color', 'HOME': '/root'},
                preexec_fn=os.setsid,
                close_fds=True,
            )
            os.close(self.slave_fd)
            self.slave_fd = None

            self._read_task = asyncio.create_task(self._forward_output())

        except Exception as exc:
            await self.send(bytes_data=f'\r\n\x1b[31mFailed to start shell: {exc}\x1b[0m\r\n'.encode())

    async def _forward_output(self):
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, os.read, self.master_fd, 4096)
                if data:
                    await self.send(bytes_data=data)
            except OSError:
                break
        try:
            await self.send(bytes_data=b'\r\n\x1b[2m[session ended]\x1b[0m\r\n')
        except Exception:
            pass

    async def receive(self, text_data=None, bytes_data=None):
        if self.master_fd is None:
            return
        if bytes_data:
            try:
                os.write(self.master_fd, bytes_data)
            except OSError:
                pass
        elif text_data:
            try:
                msg = json.loads(text_data)
                if msg.get('type') == 'resize':
                    rows = max(1, int(msg.get('rows', 24)))
                    cols = max(1, int(msg.get('cols', 80)))
                    self._set_winsize(rows, cols)
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

    def _set_winsize(self, rows, cols):
        try:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    async def disconnect(self, code):
        if self._read_task:
            self._read_task.cancel()

        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
            try:
                await asyncio.wait_for(self.process.wait(), timeout=3)
            except (asyncio.TimeoutError, Exception):
                try:
                    self.process.kill()
                except Exception:
                    pass

        for fd_attr in ('master_fd', 'slave_fd'):
            fd = getattr(self, fd_attr, None)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_attr, None)
