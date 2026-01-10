"use client"

import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import { Sidebar } from "@/components/sidebar"
import { ChatArea } from "@/components/chat-area"
import { ContextPanel } from "@/components/context-panel"
import {
  createNewChat,
  setCurrentConversationId,
  deleteConversation,
  toggleSelectedDocument,
  clearSelectedDocuments,
  fetchConversations,
} from "@/store/generalSlicer"

export default function Home() {
  const dispatch = useDispatch()
  const { conversations, currentConversationId, documents, selectedDocuments } = useSelector((state) => state.general)

  useEffect(() => {
    dispatch(fetchConversations())
  }, [dispatch])

  const handleCreateNewChat = async () => {
    dispatch(createNewChat())
    dispatch(clearSelectedDocuments())
  }

  const handleSelectConversation = (conversationId) => {
    dispatch(setCurrentConversationId(conversationId))
  }

  const handleDeleteConversation = (conversationId) => {
    dispatch(deleteConversation(conversationId))
  }

  const handleToggleDocument = (docName) => {
    dispatch(toggleSelectedDocument(docName))
  }

  return (
    <div className="h-screen flex bg-gradient-to-br from-cyan-50 via-blue-50 to-gray-50">
      <Sidebar
        currentConversationId={currentConversationId}
        onNewChat={handleCreateNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
      />
      <ChatArea />
      <ContextPanel
        documents={documents}
        selectedDocuments={selectedDocuments}
        onToggleDocument={handleToggleDocument}
      />
    </div>
  )
}
