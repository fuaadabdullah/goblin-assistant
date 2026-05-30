# GoblinOS Assistant Authentication Setup

This document explains the authentication system configuration and how to test it.

## Overview

The GoblinOS Assistant uses a hybrid authentication system that supports both Supabase and a mock authentication service for development.

## Supabase Configuration

### Environment Variables

Ensure these environment variables are set in your `.env.local` file:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Supabase Project Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Enable Email Authentication in the Authentication settings
3. Configure OAuth providers if needed (Google, GitHub, Discord)
4. Set up redirect URLs for your application

## Authentication Flow

### 1. Registration (`POST /api/auth/register`)

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "confirmPassword": "password123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful",
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "John Doe"
  },
  "session": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_at": 1234567890
  }
}
```

### 2. Login (`POST /api/auth/login`)

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "John Doe"
  },
  "session": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_at": 1234567890
  }
}
```

### 3. Session Management

- HTTP-only cookies are set for secure session management
- Tokens are automatically refreshed when needed
- Sessions expire after 24 hours

## Error Handling

The system provides detailed error messages for common issues:

- **400 Bad Request**: Invalid email format, weak password, missing fields
- **401 Unauthorized**: Invalid credentials
- **500 Internal Server Error**: Server-side issues

## Testing the Authentication

### Manual Testing

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Navigate to the login page and test:
   - User registration with valid data
   - User login with correct credentials
   - Error handling for invalid inputs

### Automated Testing

Run the test script:
```bash
node test-auth.js
```

This script will:
1. Check Supabase configuration
2. Test user registration
3. Test user login
4. Report results

## Troubleshooting

### Common Issues

1. **"Supabase is not configured"**
   - Check that environment variables are set correctly
   - Verify the `.env.local` file exists and has the right values

2. **"Login failed"**
   - Ensure the user exists in Supabase
   - Check email and password are correct
   - Verify Supabase project is active

3. **CORS Issues**
   - Ensure your Supabase project allows requests from your domain
   - Check the API URL is correct

4. **Token Issues**
   - Verify the JWT secret is configured in Supabase
   - Check token expiration settings

### Debug Mode

Enable debug logging by adding this to your environment:
```bash
DEBUG=auth:*
```

## Security Features

- Passwords are never stored in plain text
- HTTP-only cookies prevent XSS attacks
- CSRF protection with SameSite cookies
- Rate limiting on authentication endpoints
- Input validation and sanitization

## Fallback to Mock Auth

If Supabase is not configured, the system automatically falls back to a mock authentication service for development purposes. This allows you to test the frontend without a Supabase setup.

## Next Steps

1. Configure your Supabase project
2. Set up environment variables
3. Test the authentication flow
4. Customize the UI as needed
5. Add additional security measures if required
