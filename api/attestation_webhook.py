"""
Kubernetes Admission Controller for Hardware Attestation Validation
Ensures only attested nodes can run sandbox workloads
"""

import json
import os
from typing import Dict, Any
import base64

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .attestation_service import attestation_service

app = FastAPI(title="Sandbox Attestation Webhook")

class AdmissionReview(BaseModel):
    """Kubernetes AdmissionReview request/response format"""
    apiVersion: str
    kind: str
    request: Dict[str, Any]

class AdmissionResponse(BaseModel):
    """Admission controller response"""
    apiVersion: str
    kind: str
    response: Dict[str, Any]

def extract_node_name_from_pod(pod_spec: Dict[str, Any]) -> str:
    """Extract node name from pod spec"""
    return pod_spec.get('spec', {}).get('nodeName', '')

def validate_pod_attestation(pod_spec: Dict[str, Any]) -> Dict[str, bool]:
    """
    Validate that the pod is scheduled on an attested node
    Returns validation result
    """
    node_name = extract_node_name_from_pod(pod_spec)

    if not node_name:
        return {
            'allowed': False,
            'message': 'Pod does not specify nodeName - cannot validate attestation'
        }

    # Check if node is attested
    is_attested = attestation_service.is_node_attested(node_name)

    if is_attested:
        return {
            'allowed': True,
            'message': f'Node {node_name} has valid attestation'
        }
    else:
        return {
            'allowed': False,
            'message': f'Node {node_name} is not attested or attestation has expired'
        }

@app.post("/validate")
async def validate_admission(request: Request):
    """Admission controller webhook endpoint"""
    try:
        # Parse admission review
        body = await request.json()
        admission_review = AdmissionReview(**body)

        uid = admission_review.request.get('uid')
        pod = admission_review.request.get('object', {})

        # Validate pod attestation
        validation = validate_pod_attestation(pod)

        # Create admission response
        response = {
            'uid': uid,
            'allowed': validation['allowed'],
            'status': {
                'message': validation['message']
            }
        }

        # If denied, provide warning
        if not validation['allowed']:
            response['status']['code'] = 403
            response['status']['reason'] = 'Forbidden'

            # Create Kubernetes event for denied admission
            create_admission_denied_event(pod, validation['message'])

        admission_response = {
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': response
        }

        return JSONResponse(content=admission_response)

    except Exception as e:
        # On error, deny admission for security
        error_msg = f'Attestation validation error: {str(e)}'

        admission_response = {
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': body.get('request', {}).get('uid', 'unknown'),
                'allowed': False,
                'status': {
                    'code': 500,
                    'message': error_msg
                }
            }
        }

        return JSONResponse(content=admission_response, status_code=500)

def create_admission_denied_event(pod: Dict[str, Any], reason: str):
    """Create a Kubernetes event for denied admission"""
    try:
        import kubernetes
        from kubernetes import client, config

        # Load in-cluster config
        config.load_incluster_config()
        v1 = client.CoreV1Api()

        # Extract pod information
        pod_name = pod.get('metadata', {}).get('name', 'unknown')
        namespace = pod.get('metadata', {}).get('namespace', 'sandbox')
        node_name = extract_node_name_from_pod(pod)

        # Create event
        event = client.V1Event(
            metadata=client.V1ObjectMeta(
                name=f"sandbox-attestation-denied-{pod_name}",
                namespace=namespace
            ),
            involved_object=client.V1ObjectReference(
                kind="Pod",
                name=pod_name,
                namespace=namespace
            ),
            reason="AttestationValidationFailed",
            message=f"Pod admission denied due to attestation failure: {reason}",
            type="Warning",
            source=client.V1EventSource(
                component="sandbox-attestation-webhook"
            ),
            first_timestamp=None,  # Will be set by Kubernetes
            last_timestamp=None    # Will be set by Kubernetes
        )

        v1.create_namespaced_event(namespace, event)

    except Exception as e:
        # Log error but don't fail validation
        print(f"Failed to create admission denied event: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connectivity
        attested_count = len(attestation_service.list_attested_nodes())

        return {
            "status": "healthy",
            "attested_nodes": attested_count,
            "service": "attestation-webhook"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/attestation-status")
async def get_attestation_status():
    """Get current attestation status for all nodes"""
    try:
        attested_nodes = attestation_service.list_attested_nodes()
        return {
            "attested_nodes": attested_nodes,
            "total_count": len(attested_nodes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get attestation status: {str(e)}")

@app.post("/attest-node")
async def attest_node(request: Request):
    """Manually attest a node (for testing/admin purposes)"""
    try:
        data = await request.json()
        node_id = data.get('node_id')
        provider = data.get('provider', 'tpm')
        attestation_data = data.get('attestation_data', {})

        if not node_id:
            raise HTTPException(status_code=400, detail="node_id is required")

        result = attestation_service.attest_node(node_id, provider, attestation_data)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Attestation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    # For development/testing without TLS
    print("Starting attestation webhook server...")
    uvicorn.run(
        "api.attestation_webhook:app",
        host="0.0.0.0",
        port=8443,
        reload=True
    )