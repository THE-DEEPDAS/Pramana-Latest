import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = "http://localhost:8001";

let sessionId: string | null = null;

export async function POST(req: NextRequest) {
  try {
    const { message } = await req.json();

    // 🔥 Create session if not exists
    if (!sessionId) {
      const sessionRes = await fetch(`${BACKEND_URL}/chat/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title: "New Chat" }),
      });

      const sessionData = await sessionRes.json();
      sessionId = sessionData.id;
    }

    // 🔥 Send message to FastAPI
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

    return NextResponse.json({
      message: data.assistant_message.content,
      sources: data.assistant_message.meta?.sources || [],
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Preview API error:", error);

    return NextResponse.json(
      { error: "Backend failed" },
      { status: 500 }
    );
  }
}