"""
Shared pytest fixtures for virtual mesh tests.

Environment variables (match launch_debug_vms.sh):
  VIRTUAL_MESH_NODES          Number of VMs (default 2)
  VIRTUAL_MESH_SSH_BASE_PORT  First SSH port (default 2222)
  VIRTUAL_MESH_SSH_TIMEOUT    Per-command SSH timeout in seconds (default 30)
"""

import pytest
from helpers import NODES, N_NODES, ssh_run, node_mac  # noqa: F401 (re-exported)


@pytest.fixture(params=NODES, ids=[n["name"] for n in NODES])
def node(request):
    """Parametrized fixture: yields each node dict {name, port, index}."""
    return request.param


@pytest.fixture
def node1():
    return NODES[0]


@pytest.fixture
def node2():
    if N_NODES < 2:
        pytest.skip("Need at least 2 nodes")
    return NODES[1]


@pytest.fixture
def all_nodes():
    return NODES
