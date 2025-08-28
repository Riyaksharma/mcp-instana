"""
Tests for JWT Authentication functionality
"""

import pytest
import jwt
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.core.jwt_auth import TokenVerifier


class TestTokenVerifier:
    """Test cases for TokenVerifier class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.secret_key = "test-secret-key-minimum-32-chars-long"
        self.audience = "test-audience"
        self.algorithm = "HS256"
        
        self.verifier = TokenVerifier(
            public_key=self.secret_key,
            audience=self.audience,
            algorithm=self.algorithm
        )
    
    def test_extract_jwt_token_valid(self):
        """Test extracting JWT token from valid Authorization header"""
        headers = {"Authorization": "Bearer test.jwt.token"}
        token = self.verifier.extract_jwt_token(headers)
        assert token == "test.jwt.token"
    
    def test_extract_jwt_token_invalid_format(self):
        """Test extracting JWT token from invalid Authorization header"""
        headers = {"Authorization": "InvalidFormat test.jwt.token"}
        token = self.verifier.extract_jwt_token(headers)
        assert token is None
    
    def test_extract_jwt_token_missing_header(self):
        """Test extracting JWT token when Authorization header is missing"""
        headers = {}
        token = self.verifier.extract_jwt_token(headers)
        assert token is None
    
    def test_validate_jwt_token_valid(self):
        """Test validating a valid JWT token"""
        # Create a valid JWT token
        payload = {
            "aud": self.audience,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "sub": "test-user",
            "instana_token": "test-instana-token",
            "instana_base_url": "https://test.instana.io"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        result = self.verifier.validate_jwt_token(token)
        
        assert result["valid"] is True
        assert result["error"] is None
        assert result["claims"]["sub"] == "test-user"
        assert result["claims"]["instana_token"] == "test-instana-token"
    
    def test_validate_jwt_token_expired(self):
        """Test validating an expired JWT token"""
        # Create an expired JWT token
        payload = {
            "aud": self.audience,
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),
            "sub": "test-user"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        result = self.verifier.validate_jwt_token(token)
        
        assert result["valid"] is False
        assert "expired" in result["error"].lower()
    
    def test_validate_jwt_token_invalid_audience(self):
        """Test validating JWT token with invalid audience"""
        payload = {
            "aud": "wrong-audience",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "sub": "test-user"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        result = self.verifier.validate_jwt_token(token)
        
        assert result["valid"] is False
        assert "audience" in result["error"].lower()
    
    def test_validate_jwt_token_invalid_signature(self):
        """Test validating JWT token with invalid signature"""
        # Create token with wrong secret
        payload = {
            "aud": self.audience,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "sub": "test-user"
        }
        
        token = jwt.encode(payload, "wrong-secret", algorithm=self.algorithm)
        
        result = self.verifier.validate_jwt_token(token)
        
        assert result["valid"] is False
        assert "signature" in result["error"].lower()
    
    def test_validate_jwt_token_missing_required_scopes(self):
        """Test validating JWT token with missing required scopes"""
        verifier = TokenVerifier(
            public_key=self.secret_key,
            audience=self.audience,
            algorithm=self.algorithm,
            required_scopes=["read:data", "write:data"]
        )
        
        payload = {
            "aud": self.audience,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "sub": "test-user",
            "scope": "read:data"  # Missing write:data
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        result = verifier.validate_jwt_token(token)
        
        assert result["valid"] is False
        assert "scopes" in result["error"].lower()
    
    def test_get_instana_credentials_from_jwt_valid(self):
        """Test extracting Instana credentials from valid JWT claims"""
        claims = {
            "instana_token": "test-instana-token",
            "instana_base_url": "https://test.instana.io"
        }
        
        credentials = self.verifier.get_instana_credentials_from_jwt(claims)
        
        assert credentials is not None
        assert credentials[0] == "test-instana-token"
        assert credentials[1] == "https://test.instana.io"
    
    def test_get_instana_credentials_from_jwt_alternative_keys(self):
        """Test extracting Instana credentials using alternative claim keys"""
        claims = {
            "instana_api_token": "test-instana-token",
            "instana_url": "https://test.instana.io"
        }
        
        credentials = self.verifier.get_instana_credentials_from_jwt(claims)
        
        assert credentials is not None
        assert credentials[0] == "test-instana-token"
        assert credentials[1] == "https://test.instana.io"
    
    def test_get_instana_credentials_from_jwt_missing(self):
        """Test extracting Instana credentials when they are missing"""
        claims = {
            "sub": "test-user",
            "aud": "test-audience"
        }
        
        credentials = self.verifier.get_instana_credentials_from_jwt(claims)
        
        assert credentials is None
    
    def test_get_instana_credentials_from_jwt_partial(self):
        """Test extracting Instana credentials when only one is present"""
        claims = {
            "instana_token": "test-instana-token"
            # Missing instana_base_url
        }
        
        credentials = self.verifier.get_instana_credentials_from_jwt(claims)
        
        assert credentials is None


class TestTokenVerifierWithJWKS:
    """Test cases for TokenVerifier with JWKS endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.jwks_uri = "https://test.auth.com/.well-known/jwks.json"
        self.audience = "test-audience"
        
        self.verifier = TokenVerifier(
            jwks_uri=self.jwks_uri,
            audience=self.audience,
            algorithm="RS256"
        )
    
    @patch('src.core.jwt_auth.requests.get')
    def test_fetch_jwks_keys_success(self, mock_get):
        """Test successful JWKS key fetching"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [
                {
                    "kid": "test-key-1",
                    "kty": "RSA",
                    "n": "test-n",
                    "e": "AQAB"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        keys = self.verifier._fetch_jwks_keys()
        
        assert "test-key-1" in keys
        assert keys["test-key-1"]["kty"] == "RSA"
    
    @patch('src.core.jwt_auth.requests.get')
    def test_fetch_jwks_keys_failure(self, mock_get):
        """Test JWKS key fetching failure"""
        mock_get.side_effect = Exception("Network error")
        
        keys = self.verifier._fetch_jwks_keys()
        
        # Should return empty dict on failure
        assert keys == {}


class TestTokenVerifierInitialization:
    """Test cases for TokenVerifier initialization"""
    
    def test_init_with_public_key(self):
        """Test initialization with public key"""
        verifier = TokenVerifier(
            public_key="test-public-key",
            audience="test-audience"
        )
        
        assert verifier.public_key == "test-public-key"
        assert verifier.audience == "test-audience"
        assert verifier.algorithm == "RS256"  # Default
    
    def test_init_with_jwks_uri(self):
        """Test initialization with JWKS URI"""
        verifier = TokenVerifier(
            jwks_uri="https://test.auth.com/.well-known/jwks.json",
            audience="test-audience"
        )
        
        assert verifier.jwks_uri == "https://test.auth.com/.well-known/jwks.json"
        assert verifier.audience == "test-audience"
    
    def test_init_with_required_scopes(self):
        """Test initialization with required scopes"""
        verifier = TokenVerifier(
            public_key="test-key",
            audience="test-audience",
            required_scopes=["read:data", "write:data"]
        )
        
        assert verifier.required_scopes == ["read:data", "write:data"]
    
    def test_init_with_custom_algorithm(self):
        """Test initialization with custom algorithm"""
        verifier = TokenVerifier(
            public_key="test-key",
            audience="test-audience",
            algorithm="HS256"
        )
        
        assert verifier.algorithm == "HS256"
