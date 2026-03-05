// app/api/auth/register/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { authService } from '../../../lib/services/auth-service';
import { handleApiError, AppError } from '../../../../lib/error-handler';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password, confirmPassword, name } = body;

    if (!email || !password || !confirmPassword) {
      throw new AppError('Email, password, and confirm password are required', 400);
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      throw new AppError('Invalid email format', 400);
    }

    // Validate password length
    if (password.length < 6) {
      throw new AppError('Password must be at least 6 characters long', 400);
    }

    // Validate password confirmation
    if (password !== confirmPassword) {
      throw new AppError('Passwords do not match', 400);
    }

    // Validate name
    if (!name || name.trim().length < 2) {
      throw new AppError('Name must be at least 2 characters long', 400);
    }

    const authData = await authService.signUp(email, password, name.trim());

    if (!authData || !authData.user) {
      throw new AppError('Registration failed', 400);
    }

    // Create response with proper data structure
    const responseData = {
      success: true,
      message: 'Registration successful',
      user: {
        id: authData.user.id,
        email: authData.user.email,
        name: authData.user.name,
      },
      session: authData.session,
    };

    // Create response
    const response = NextResponse.json(responseData);

    // Set session cookie if we have a session
    if (authData.session?.access_token) {
      response.cookies.set('auth_token', authData.session.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 24 * 60 * 60, // 24 hours
        path: '/',
      });
    }

    return response;

  } catch (error) {
    console.error('Register API error:', error);
    return handleApiError(error);
  }
}
