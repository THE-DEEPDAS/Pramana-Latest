import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = "http://localhost:8001";

let sessionId: string | null = null;

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();

    if (!message) {
      return NextResponse.json(
        { error: "Message is required" },
        { status: 400 }
      );
    }

    //  STEP 1: Create session if not exists
    if (!sessionId) {
      const sessionRes = await fetch(`${BACKEND_URL}/chat/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: "New Chat",
        }),
      });

      const sessionData = await sessionRes.json();
      sessionId = sessionData.id;
    }

    //  STEP 2: Send message to backend
    const res = await fetch(
      `${BACKEND_URL}/chat/sessions/${sessionId}/messages`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: message,
        }),
      }
    );

    const data = await res.json();

    //  STEP 3: Return formatted response to frontend
    return NextResponse.json({
      message: data.assistant_message.content,
      sources: data.assistant_message.meta?.sources || [],
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Chat API error:", error);

    return NextResponse.json(
      { error: "Backend connection failed" },
      { status: 500 }
    );
  }
}