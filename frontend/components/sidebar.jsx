"use client"

import { Button } from "@/components/ui/button"
import { Plus, X } from "lucide-react"
import { useSelector } from "react-redux"

export function Sidebar({
  // conversations,
  currentConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
}) {
  const {conversations} = useSelector((state) => state.general)
  return (
    <div className="w-60 bg-white/92 border-r border-slate-200 p-5 flex flex-col shadow-lg">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">💬 Chats</h2>
        <Button onClick={onNewChat} className="w-full bg-sky-500 hover:bg-sky-600 text-white rounded-lg">
          <Plus className="w-4 h-4 mr-2" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-3">Recent</h3>
            <div className="space-y-2">
              {conversations.map((chat) => (
                <div key={chat.id} className="flex gap-2 group">
                  <button
                    onClick={() => onSelectConversation(chat.id)}
                    className={`flex-1 text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      currentConversationId === chat.id
                        ? "bg-blue-100 text-blue-900 font-medium"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    {currentConversationId === chat.id && "🔵 "}
                    {chat.title}
                  </button>
                  <button
                    onClick={() => onDeleteConversation(chat.id)}
                    className="px-2 py-2 text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
