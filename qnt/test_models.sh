#!/bin/bash
echo "Testing model availability on this account..."
echo ""

MODELS=(
  "gemini-3.1-flash-lite-preview"
  "gemini-3-flash-preview"
  "gemini-2.5-flash"
  "gemini-3.1-pro-preview-customtools"
  "gemini-2.5-pro"
  "gemini-2.5-flash-lite"
)

for MODEL in "${MODELS[@]}"; do
  echo -n "Testing $MODEL... "
  
  # Use qnt with explicit model override
  # (we'll add a --model flag if it doesn't exist, but we checked help)
  RESULT=$(timeout 15 qnt \
    -p "reply: OK" \
    --model "$MODEL" \
    2>&1 | tail -1)
  
  if echo "$RESULT" | grep -q "OK"; then
    echo "✅ AVAILABLE"
  elif echo "$RESULT" | grep -q "429\|quota"; then
    echo "⚠️  QUOTA (available but limited)"
  elif echo "$RESULT" | grep -q "404\|not found"; then
    echo "❌ NOT AVAILABLE (404)"
  else
    echo "❓ UNKNOWN: $RESULT"
  fi
  
  sleep 2
done
