"use client"

import { ScrollArea } from "@/components/ui/scroll-area"


export function ChatMessages({ messages, isLoading }) {
  return (
    <ScrollArea className="flex-1 p-6">
      {messages.length === 0 ? (
        <div className="text-center text-slate-500 py-8">Start the conversation by asking a question!</div>
      ) : (
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  msg.role === "user" ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-900"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
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
