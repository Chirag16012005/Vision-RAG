"use client"

import { useDispatch, useSelector } from "react-redux"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { FileUpload } from "./tabs/file-upload"
import { UrlIngestion } from "./tabs/url-ingestion"
import { TopicSearch } from "./tabs/topic-search"
import { ChatMessages } from "./chat-messages"
import { sendMessage, addLocalMessage } from "@/store/generalSlicer"

export function ChatArea() {
  const dispatch = useDispatch()
  const { currentConversationId, messages, isSending, selectedDocuments } = useSelector((state) => state.general)
  const hasSelectedDocuments = selectedDocuments.length > 0

  const handleSendMessage = async (e) => {
    e.preventDefault()
    const inputElement = e.target.elements[0]
    const userQuery = inputElement?.value ?? ""

    if (!userQuery.trim() || !currentConversationId || !hasSelectedDocuments) {
      return
    }

    const userMessage = {
      role: "user",
      content: userQuery,
      id: `user_${Date.now()}`,
    }

    dispatch(addLocalMessage(userMessage))
    if (inputElement) {
      inputElement.value = ""
    }

    dispatch(
      sendMessage({
        conversationId: currentConversationId,
        userQuery,
        selectedDocuments,
      }),
    )
  }

  if (!currentConversationId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-slate-800 mb-2">Start a New Chat</h2>
          <p className="text-slate-600">Select or create a chat to get started</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-white/92 border-r border-slate-200 m-4 rounded-2xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-xl font-semibold text-slate-900">
          🧠 Chat: <code className="text-sm bg-slate-100 px-2 py-1 rounded">{currentConversationId}</code>
        </h2>
      </div>

      {/* Tabs for Upload, URL, Search */}
      <Tabs defaultValue="upload" className="flex flex-col border-b border-slate-200">
        <TabsList className="w-full justify-start px-6 py-4 bg-transparent border-b border-slate-200 rounded-none">
          <TabsTrigger value="upload" className="gap-2">
            📄 Upload File
          </TabsTrigger>
          <TabsTrigger value="url" className="gap-2">
            🔗 Add URL
          </TabsTrigger>
          <TabsTrigger value="search" className="gap-2">
            🌍 Topic Search
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="flex-1 p-6 m-0">
          <FileUpload conversationId={currentConversationId} />
        </TabsContent>

        <TabsContent value="url" className="flex-1 p-6 m-0">
          <UrlIngestion conversationId={currentConversationId} />
        </TabsContent>

        <TabsContent value="search" className="flex-1 p-6 m-0">
          <TopicSearch conversationId={currentConversationId} />
        </TabsContent>
      </Tabs>

      {/* Chat Messages */}
      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        <ChatMessages
          messages={messages}
          isLoading={isSending}
          conversationId={currentConversationId}
        />

        {/* Chat Input */}
        <form onSubmit={handleSendMessage} className="p-6 border-t border-slate-200">
          <div className="flex gap-3">
            <Input
              placeholder="Ask about your data..."
              disabled={isSending || !hasSelectedDocuments}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={isSending || !hasSelectedDocuments}
              className="bg-sky-500 hover:bg-sky-600 text-white"
            >
              Send
            </Button>
          </div>
          {!hasSelectedDocuments && (
            <p className="text-xs text-amber-600 mt-2">Select at least one document to send messages</p>
          )}
        </form>
      </div>
    </div>
  )
}
