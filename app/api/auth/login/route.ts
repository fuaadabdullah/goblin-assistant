// app/api/auth/login/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { authService } from '../../../lib/services/auth-service';
import { handleApiError, AppError } from '../../../../lib/error-handler';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, password } = body;

    if (!email || !password) {
      throw new AppError('Email and password are required', 400);
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

    const authData = await authService.signIn(email, password);

    if (!authData || !authData.user) {
      throw new AppError('Invalid email or password', 401);
    }

    // Create response with proper data structure
    const responseData = {
      success: true,
      message: 'Login successful',
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
      response.cookies.set('auth-token', authData.session.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 24 * 60 * 60, // 24 hours
        path: '/',
      });
    }

    return response;

  } catch (error) {
    console.error('Login API error:', error);
    return handleApiError(error);
  }
}