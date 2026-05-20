#!/bin/bash

# Verify SiliconeFlow API Key and Endpoint
echo "🔍 SiliconeFlow API Verification"
echo "================================="
echo ""

# Load API key from .env.local
source .env.local 2>/dev/null

if [ -z "$SILICONEFLOW_API_KEY" ]; then
    echo "❌ SILICONEFLOW_API_KEY not found in .env.local"
    exit 1
fi

echo "✅ API Key loaded: ${SILICONEFLOW_API_KEY:0:12}...${SILICONEFLOW_API_KEY: -4}"
echo "   Length: ${#SILICONEFLOW_API_KEY} characters"
echo ""

# Test different possible endpoints
ENDPOINTS=(
    "https://api.siliconflow.cn/v1/chat/completions"
    "https://api.siliconflow.com/v1/chat/completions"
    "https://cloud.siliconflow.cn/v1/chat/completions"
)

MODEL="Qwen/Qwen2.5-7B-Instruct"

for ENDPOINT in "${ENDPOINTS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔗 Testing endpoint: $ENDPOINT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST "$ENDPOINT" \
        -H "Authorization: Bearer $SILICONEFLOW_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$MODEL\",
            \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}],
            \"max_tokens\": 10
        }")
    
    # Extract HTTP code
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")
    
    echo "   HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ SUCCESS!"
        echo "   Response: $BODY" | jq -r '.choices[0].message.content' 2>/dev/null || echo "$BODY"
        echo ""
        echo "🎉 Found working endpoint: $ENDPOINT"
        exit 0
    else
        echo "   ❌ FAILED"
        echo "   Error: $BODY"
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "❌ All endpoints failed"
echo ""
echo "Possible issues:"
echo "1. Invalid API key format"
echo "2. API key not activated"
echo "3. Different authentication method required"
echo "4. Wrong endpoint URLs"
echo ""
echo "Next steps:"
echo "- Check SiliconeFlow documentation: https://docs.siliconflow.cn"
echo "- Verify API key at: https://cloud.siliconflow.cn/account/ak"
echo "- Contact SiliconeFlow support if key should be valid"
