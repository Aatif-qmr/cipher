#!/bin/bash
# Syncs Order Flow data from M2 to M1
set -a
source /Users/aatifquamre/masterbot/.env
set +a

M2_IP=$(grep M2_TAILSCALE_IP /Users/aatifquamre/masterbot/.env | cut -d= -f2)
M2_PATH="/Users/azmatsaif/masterbot/qnt/oracle/order_flow_state.json"
M1_PATH="/Users/aatifquamre/masterbot/qnt/oracle/order_flow_state.json"

# Ensure directory exists on M1
mkdir -p "$(dirname "$M1_PATH")"

echo "📡 Syncing Order Flow from M2..."
scp -q azmatsaif@$M2_IP:$M2_PATH $M1_PATH
