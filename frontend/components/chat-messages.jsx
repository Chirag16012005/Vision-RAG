"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"


export function ChatMessages({ messages, isLoading }) {
  return (
    <ScrollArea className="flex-1 min-h-0 p-6">
      {messages.length === 0 ? (
        <div className="text-center text-slate-500 py-8">Start the conversation by asking a question!</div>
      ) : (
        <div className="space-y-4">
          {messages.map((msg, idx) => {
            const isUser = msg.role === "user"

            return (
              <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      isUser ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-900"
                    }`}
                  >
                    {msg.content}
                  </div>
                  {!isUser && (
                    <Button size="sm" variant="outline" className="text-xs">
                      Give Feedback
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 text-slate-900 px-4 py-2 rounded-lg">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </ScrollArea>
  )
}
