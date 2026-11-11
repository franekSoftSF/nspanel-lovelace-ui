"""Fixtures for the nspanel_lovelace_ui tests."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
import shutil

import pytest

from homeassistant.core import HomeAssistant

FIXTURES = Path(__file__).parent / "fixtures"
RECV = "tele/nspanel_test/RESULT"
SEND = "cmnd/nspanel_test/CustomSend"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ from the repository root."""
    return


@pytest.fixture(autouse=True)
async def unload_mqtt(hass: HomeAssistant):
    """Let the mocked MQTT client's 1 s misc timer fire once before the cleanup check.

    With the mocked client the timer is not rescheduled after its first run, but a test
    shorter than 1 s would otherwise end with it pending ("Lingering timer").
    """
    yield
    if hass.config_entries.async_entries("mqtt"):
        await asyncio.sleep(1.1)
        await hass.async_block_till_done()


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    """Each test gets its own config folder (files must not leak between tests)."""
    hass.config.config_dir = str(tmp_path)
    return tmp_path


@pytest.fixture
def panels_file(hass: HomeAssistant) -> Path:
    """Copy the sample panels.yaml into the test config folder."""
    target = Path(hass.config.path("nspanel_lovelace_ui", "panels.yaml"))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "panels.yaml", target)
    return target


async def wait_for(hass: HomeAssistant, predicate: Callable[[], bool], timeout: float = 10,
                   block: bool = True) -> None:
    """Let worker threads and the loop run until predicate() holds.

    block=False while a long-running task (an update install) is pending: async_block_till_done
    would wait for that task too.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError("condition not reached in time")
        await asyncio.sleep(0.02)
        if block:
            await hass.async_block_till_done()


def published(mqtt_mock, topic: str = SEND) -> list[str]:
    """Payloads published to a topic, in order."""
    result = []
    for call in mqtt_mock.async_publish.call_args_list:
        if call.args[0] == topic:
            result.append(call.args[1])
    return result
