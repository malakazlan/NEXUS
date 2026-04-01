"""Verify NEXUS kernel boots, registers tools, and shuts down cleanly."""

import asyncio
import sys


async def test_boot():
    from nexus.kernel.kernel import Kernel

    print("Creating kernel...")
    k = Kernel()

    print("Booting kernel...")
    await k.boot()

    tools = k.tool_registry.list_tools()
    print(f"✓ Booted OK. {len(tools)} tools registered:")
    for t in tools:
        print(f"  - {t.name}: {t.description[:60]}")

    # Verify event history
    history = k.event_bus.get_history()
    print(f"✓ {len(history)} events in history")

    # Verify shared memory
    await k.shared_memory.set("test_key", "test_value")
    val = k.shared_memory.get("test_key")
    assert val == "test_value", f"Expected 'test_value', got {val}"
    print("✓ Shared memory works")

    # Verify tool schemas are LLM-compatible
    llm_tools = k.tool_registry.list_for_llm()
    print(f"✓ {len(llm_tools)} tools in LLM format")
    for t in llm_tools:
        assert t["type"] == "function"
        assert "name" in t["function"]
        print(f"  - {t['function']['name']}")

    print("Shutting down...")
    await k.shutdown()
    print("✓ Shutdown OK")
    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(test_boot())
