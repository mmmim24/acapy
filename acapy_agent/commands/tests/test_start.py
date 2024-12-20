import sys
from unittest import IsolatedAsyncioTestCase

from acapy_agent.tests import mock

from ...config.error import ArgsParseError
from .. import start as test_module


class TestStart(IsolatedAsyncioTestCase):
    def test_bad_args(self):
        with self.assertRaises(ArgsParseError):
            test_module.execute([])

        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    async def test_start_shutdown_app(self):
        mock_conductor = mock.MagicMock(
            setup=mock.CoroutineMock(),
            start=mock.CoroutineMock(),
            stop=mock.CoroutineMock(),
        )
        await test_module.start_app(mock_conductor)
        await test_module.shutdown_app(mock_conductor)

    def test_exec_start(self):
        with (
            mock.patch.object(
                # Normally this would be a CoroutineMock. However, it is awaited by
                # run_loop, which is mocked out. So we mock it as a MagicMock.
                test_module,
                "start_app",
                mock.MagicMock(),
            ) as start_app,
            mock.patch.object(test_module, "run_loop") as run_loop,
            mock.patch.object(
                # Same here as note above
                test_module,
                "shutdown_app",
                mock.MagicMock(),
            ) as shutdown_app,
            mock.patch.object(test_module, "uvloop", mock.MagicMock()) as mock_uvloop,
        ):
            mock_uvloop.install = mock.MagicMock()
            test_module.execute(
                [
                    "-it",
                    "http",
                    "0.0.0.0",
                    "80",
                    "-ot",
                    "http",
                    "--endpoint",
                    "0.0.0.0",
                    "80",
                    "--no-ledger",
                    "--wallet-test",
                ]
            )
            start_app.assert_called_once()
            assert isinstance(start_app.call_args[0][0], test_module.Conductor)
            shutdown_app.assert_called_once()
            assert isinstance(shutdown_app.call_args[0][0], test_module.Conductor)
            run_loop.assert_called_once()

    async def test_run_loop(self):
        startup = mock.CoroutineMock()
        startup_call = startup()
        shutdown = mock.CoroutineMock()
        shutdown_call = shutdown()
        with mock.patch.object(test_module, "asyncio", autospec=True) as mock_asyncio:
            test_module.run_loop(startup_call, shutdown_call)
            mock_add = mock_asyncio.get_event_loop.return_value.add_signal_handler
            mock_add.assert_called_once()
            init_coro = mock_asyncio.ensure_future.call_args[0][0]
            mock_asyncio.get_event_loop.return_value.run_forever.assert_called_once()
            await init_coro
            startup.assert_awaited_once()

            done_calls = (
                mock_asyncio.get_event_loop.return_value.add_signal_handler.call_args
            )
            done_calls[0][1]()  # exec partial
            done_coro = mock_asyncio.ensure_future.call_args[0][0]
            tasks = [
                mock.MagicMock(),
                mock.MagicMock(cancel=mock.MagicMock()),
            ]
            mock_asyncio.gather = mock.CoroutineMock()

            if sys.version_info.major == 3 and sys.version_info.minor > 6:
                mock_asyncio.all_tasks.return_value = tasks
                mock_asyncio.current_task.return_value = tasks[0]
            else:
                mock_asyncio.Task.all_tasks.return_value = tasks
                mock_asyncio.Task.current_task.return_value = tasks[0]

            await done_coro
            shutdown.assert_awaited_once()

    async def test_run_loop_init_x(self):
        startup = mock.CoroutineMock(side_effect=KeyError("the front fell off"))
        startup_call = startup()
        shutdown = mock.CoroutineMock()
        shutdown_call = shutdown()
        with (
            mock.patch.object(test_module, "asyncio", autospec=True) as mock_asyncio,
            mock.patch.object(test_module, "LOGGER", autospec=True) as mock_logger,
        ):
            test_module.run_loop(startup_call, shutdown_call)
            mock_add = mock_asyncio.get_event_loop.return_value.add_signal_handler
            mock_add.assert_called_once()
            init_coro = mock_asyncio.ensure_future.call_args[0][0]
            mock_asyncio.get_event_loop.return_value.run_forever.assert_called_once()
            await init_coro
            startup.assert_awaited_once()

            done_calls = (
                mock_asyncio.get_event_loop.return_value.add_signal_handler.call_args
            )
            done_calls[0][1]()  # exec partial
            done_coro = mock_asyncio.ensure_future.call_args[0][0]
            task = mock.MagicMock()
            mock_asyncio.gather = mock.CoroutineMock()

            if sys.version_info.major == 3 and sys.version_info.minor > 6:
                mock_asyncio.all_tasks.return_value = [task]
                mock_asyncio.current_task.return_value = task
            else:
                mock_asyncio.Task.all_tasks.return_value = [task]
                mock_asyncio.Task.current_task.return_value = task

            await done_coro
            shutdown.assert_awaited_once()
            mock_logger.exception.assert_called_once()

    def test_main(self):
        with (
            mock.patch.object(test_module, "__name__", "__main__") as mock_name,
            mock.patch.object(test_module, "execute", mock.MagicMock()) as mock_execute,
        ):
            test_module.main()
            mock_execute.assert_called_once
