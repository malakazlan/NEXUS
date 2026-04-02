"""Tests for agent-to-agent messaging via EventBus."""

import asyncio
import pytest
from nexus.events.bus import EventBus
from nexus.events.types import EventType
from nexus.agents.messaging import AgentMessage, MessageRouter


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def router(event_bus):
    return MessageRouter(event_bus)


@pytest.mark.asyncio
async def test_send_and_receive(router):
    received = []

    async def handler(msg: AgentMessage):
        received.append(msg)

    router.register_handler("agent-b", handler)
    await router.send(
        from_agent="agent-a",
        to_agent="agent-b",
        content="hello from A",
        message_type="request",
    )
    await asyncio.sleep(0.05)

    assert len(received) == 1
    assert received[0].from_agent == "agent-a"
    assert received[0].to_agent == "agent-b"
    assert received[0].content == "hello from A"
    assert received[0].message_type == "request"


@pytest.mark.asyncio
async def test_broadcast(router):
    received_b = []
    received_c = []

    async def handler_b(msg: AgentMessage):
        received_b.append(msg)

    async def handler_c(msg: AgentMessage):
        received_c.append(msg)

    router.register_handler("agent-b", handler_b)
    router.register_handler("agent-c", handler_c)

    await router.broadcast(
        from_agent="agent-a",
        content="hello everyone",
    )
    await asyncio.sleep(0.05)

    assert len(received_b) == 1
    assert len(received_c) == 1
    assert received_b[0].content == "hello everyone"
    assert received_b[0].message_type == "broadcast"


@pytest.mark.asyncio
async def test_unregister_handler(router):
    received = []

    async def handler(msg: AgentMessage):
        received.append(msg)

    router.register_handler("agent-b", handler)
    router.unregister_handler("agent-b")

    await router.send(
        from_agent="agent-a",
        to_agent="agent-b",
        content="should not arrive",
        message_type="request",
    )
    await asyncio.sleep(0.05)
    assert len(received) == 0


@pytest.mark.asyncio
async def test_correlation_id_round_trip(router):
    received = []

    async def handler(msg: AgentMessage):
        received.append(msg)

    router.register_handler("agent-b", handler)
    await router.send(
        from_agent="agent-a",
        to_agent="agent-b",
        content="what is 2+2?",
        message_type="request",
        correlation_id="req-001",
    )
    await asyncio.sleep(0.05)

    assert received[0].correlation_id == "req-001"
