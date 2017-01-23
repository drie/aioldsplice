import asyncio
import asynctest
import aioldsplice
import socket


class TestConcerns(asynctest.TestCase):

    async def setUp(self):
        self._l, self._r = socket.socketpair()

    async def tearDown(self):
        self._l.close()
        self._r.close()

    async def test_concerns(self):
        # should return imediately
        await aioldsplice.writer_ready(self._l, _loop=self.loop)
        # should time out
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(aioldsplice.reader_ready(self._r, _loop=self.loop), 0.1)
        self._l.sendall(b"test")
        await aioldsplice.reader_ready(self._r, _loop=self.loop)

    def test_concern_cancel(self):
        wc = aioldsplice.writer_ready(self._l, _loop=self.loop)
        wc.cancel()
        rc = aioldsplice.reader_ready(self._l, _loop=self.loop)
        rc.cancel()


class TestProxy(asynctest.TestCase):

    _test_msg = b"testing 1234"
    _test_return_msg = None

    async def setUp(self):
        server_listener_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_listener_conn = server_listener_conn
        server_listener_conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_listener_conn.bind(('', 0))
        server_listener_conn.listen(5)
        server_listener_conn.setblocking(0)

        self.client_conn = client_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_conn.setblocking(0)
        client_conn.connect_ex(server_listener_conn.getsockname())
        await aioldsplice.reader_ready(server_listener_conn)
        server_conn, server_addr = server_listener_conn.accept()
        self.server_conn = server_conn
        server_conn.setblocking(0)

    def tearDown(self):
        self.client_conn.close()
        self.server_conn.close()
        self.server_listener_conn.close()

    async def __test_proxy_then_(self):
        proxy_task = self.loop.create_task(aioldsplice.proxy(self.server_conn, self.server_conn,
                                                             _loop=self.loop))
        self.client_conn.sendall(self._test_msg)
        await aioldsplice.reader_ready(self.client_conn)
        self._test_return_msg = self.client_conn.recv(1024)
        return proxy_task

    async def test_proxy_then_client_shutdown(self):
        proxy_task = await self.__test_proxy_then_()
        self.client_conn.close()
        await proxy_task
        self.assertEqual(self._test_return_msg, self._test_msg)

    @asynctest.patch('aioldsplice.writer_ready', wraps=aioldsplice.writer_ready)
    async def test_proxy_when_writer_isnt_ready(self, writer_ready_mock):
        proxy_task = await self.__test_proxy_then_()
        for i in range(0, 100):
            self.client_conn.sendall(b"a" * 1024 * 1024)
            try:
                await asyncio.wait_for(aioldsplice.writer_ready(self.client_conn), 0.1)
            except asyncio.TimeoutError:
                break
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(aioldsplice.writer_ready(self.client_conn), 0.1)

        self.assertTrue(writer_ready_mock.called)
        while True:
            try:
                self.client_conn.recv(1024 * 1024)
            except BlockingIOError:
                break
        self.client_conn.close()

        with self.assertRaises(BrokenPipeError):
            await proxy_task
        self.assertEqual(self._test_return_msg, self._test_msg)

    async def __test_proxy_connection_writer_timeout(self):
        proxy_task = await self.__test_proxy_then_()
        for i in range(0, 100):
            self.client_conn.sendall(b"a" * 1024 * 1024)
            try:
                await asyncio.wait_for(aioldsplice.writer_ready(self.client_conn), 0.1)
            except asyncio.TimeoutError:
                break
        with self.assertRaises(asyncio.TimeoutError):
            await proxy_task
