import { createSlice, createAsyncThunk } from "@reduxjs/toolkit"
import axios from "axios"

const BACKEND_URL = "http://localhost:8007"

// ==================== CONVERSATION THUNKS ====================
export const createNewChat = createAsyncThunk("general/createNewChat", async (_, { rejectWithValue }) => {
  try {
    const response = await axios.post(
      `${BACKEND_URL}/qa/chat/new`,
      { user_id: "general" },
      { headers: { "Content-Type": "application/json" }, withCredentials: true },
    )
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const fetchConversations = createAsyncThunk("general/fetchConversations", async (_, { rejectWithValue }) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/qa/conversations`, { withCredentials: true })
    return response.data.conversations
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const deleteConversation = createAsyncThunk(
  "general/deleteConversation",
  async (conversationId, { rejectWithValue }) => {
    try {
      await axios.delete(`${BACKEND_URL}/qa/conversations/${conversationId}`, { withCredentials: true })
      return conversationId
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

export const fetchConversationHistory = createAsyncThunk(
  "general/fetchConversationHistory",
  async (conversationId, { rejectWithValue }) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/qa/conversations/${conversationId}/history`, {
        withCredentials: true,
      })
      return response.data
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

// ==================== DOCUMENT THUNKS ====================
export const uploadFile = createAsyncThunk(
  "general/uploadFile",
  async ({ file, conversationId }, { rejectWithValue }) => {
    try {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("conversation_id", conversationId)

      const response = await axios.post(`${BACKEND_URL}/ingest/document`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        withCredentials: true,
      })
      return response.data
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

export const ingestUrl = createAsyncThunk("general/ingestUrl", async ({ url, conversationId }, { rejectWithValue }) => {
  try {
    // Calls the correct ingestion endpoint
    const response = await axios.post(
      `${BACKEND_URL}/ingest/url?conversation_id=${conversationId}`,
      { url },
      { headers: { "Content-Type": "application/json" }, withCredentials: true },
    )
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const searchTopic = createAsyncThunk("general/searchTopic", async ({ topic, seenUrls }, { rejectWithValue }) => {
  try {
    const response = await axios.post(
      `${BACKEND_URL}/ingest/search/query`,
      { topic, seen_urls: seenUrls },
      { headers: { "Content-Type": "application/json" }, withCredentials: true },
    )
    return response.data
  } catch (error) {
    return rejectWithValue(error.response?.data || error.message)
  }
})

export const ingestTopic = createAsyncThunk(
  "general/ingestTopic",
  async ({ topic, conversationId }, { rejectWithValue }) => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/ingest/search/query?conversation_id=${conversationId}`,
        { topic },
        { headers: { "Content-Type": "application/json" }, withCredentials: true },
      )
      return response.data
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

export const fetchDocuments = createAsyncThunk(
  "general/fetchDocuments",
  async (conversationId, { rejectWithValue }) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/qa/conversations/${conversationId}/documents`, {
        withCredentials: true,
      })
      return response.data.documents
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

// ==================== CHAT THUNKS ====================
export const sendMessage = createAsyncThunk(
  "general/sendMessage",
  async ({ conversationId, userQuery, selectedDocuments }, { rejectWithValue }) => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/qa/conversations/${conversationId}`,
        {
          user_query: userQuery,
          selected_documents: Array.from(selectedDocuments),
        },
        { headers: { "Content-Type": "application/json" }, withCredentials: true },
      )
      return response.data
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

export const submitFeedback = createAsyncThunk(
  "general/submitFeedback",
  async ({ conversationId, messageId, rating }, { rejectWithValue }) => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/qa/chat/feedback`,
        { conversation_id: conversationId, message_id: messageId, rating },
        { headers: { "Content-Type": "application/json" }, withCredentials: true },
      )
      return response.data
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message)
    }
  },
)

// ==================== INITIAL STATE ====================
const initialState = {
  // Conversations
  conversations: [],
  currentConversationId: null,

  // Messages
  messages: [],

  // Documents
  documents: [],
  selectedDocuments: [],

  // Topic Search
  topicSearchResults: [],

  // UI States
  isLoading: false,
  isSending: false,
  isUploading: false,
  isSearching: false,

  // Error handling
  error: null,
}

// ==================== SLICE ====================
export const generalSlice = createSlice({
  name: "general",
  initialState,
  reducers: {
    setCurrentConversationId(state, action) {
      state.currentConversationId = action.payload
    },

    toggleSelectedDocument(state, action) {
      const docName = action.payload
      const existingIndex = state.selectedDocuments.indexOf(docName)

      if (existingIndex !== -1) {
        state.selectedDocuments.splice(existingIndex, 1)
      } else {
        state.selectedDocuments.push(docName)
      }
    },

    clearSelectedDocuments(state) {
      state.selectedDocuments = []
    },

    setSelectedDocuments(state, action) {
      state.selectedDocuments = Array.from(new Set(action.payload))
    },

    clearTopicSearchResults(state) {
      state.topicSearchResults = []
    },

    clearError(state) {
      state.error = null
    },

    clearMessages(state) {
      state.messages = []
    },

    addLocalMessage(state, action) {
      state.messages.push(action.payload)
    },
  },

  extraReducers: (builder) => {
    // ==================== CREATE NEW CHAT ====================
    builder
      .addCase(createNewChat.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(createNewChat.fulfilled, (state, action) => {
        state.isLoading = false
        state.conversations.push(action.payload)
        state.currentConversationId = action.payload.conversation_id
        state.messages = []
        state.documents = []
        state.selectedDocuments = []
      })
      .addCase(createNewChat.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== FETCH CONVERSATIONS ====================
    builder
      .addCase(fetchConversations.pending, (state) => {
        state.isLoading = true
      })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.isLoading = false
        state.conversations = action.payload
      })
      .addCase(fetchConversations.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== DELETE CONVERSATION ====================
    builder
      .addCase(deleteConversation.pending, (state) => {
        state.isLoading = true
      })
      .addCase(deleteConversation.fulfilled, (state, action) => {
        state.isLoading = false
        state.conversations = state.conversations.filter((c) => c.id !== action.payload)
        if (state.currentConversationId === action.payload) {
          state.currentConversationId = null
          state.messages = []
          state.documents = []
          state.selectedDocuments = []
        }
      })
      .addCase(deleteConversation.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== FETCH CONVERSATION HISTORY ====================
    builder
      .addCase(fetchConversationHistory.pending, (state) => {
        state.isLoading = true
      })
      .addCase(fetchConversationHistory.fulfilled, (state, action) => {
        state.isLoading = false
        state.messages = action.payload.messages.map((m) => ({
          role: m.role === "human" ? "user" : "assistant",
          content: m.text,
          id: m.id,
        }))
      })
      .addCase(fetchConversationHistory.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== UPLOAD FILE ====================
    builder
      .addCase(uploadFile.pending, (state) => {
        state.isUploading = true
        state.error = null
      })
      .addCase(uploadFile.fulfilled, (state, action) => {
        state.isUploading = false
        state.documents = action.payload.document_names
      })
      .addCase(uploadFile.rejected, (state, action) => {
        state.isUploading = false
        state.error = action.payload
      })

    // ==================== INGEST URL ====================
    builder
      .addCase(ingestUrl.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(ingestUrl.fulfilled, (state, action) => {
        state.isLoading = false
        // Refresh documents after successful ingestion
      })
      .addCase(ingestUrl.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== SEARCH TOPIC ====================
    builder
      .addCase(searchTopic.pending, (state) => {
        state.isSearching = true
        state.error = null
      })
      .addCase(searchTopic.fulfilled, (state, action) => {
        state.isSearching = false
        state.topicSearchResults = action.payload.results || []
      })
      .addCase(searchTopic.rejected, (state, action) => {
        state.isSearching = false
        state.error = action.payload
      })

    // ==================== INGEST TOPIC ====================
    builder
      .addCase(ingestTopic.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(ingestTopic.fulfilled, (state, action) => {
        state.isLoading = false
        state.topicSearchResults = []
      })
      .addCase(ingestTopic.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== FETCH DOCUMENTS ====================
    builder
      .addCase(fetchDocuments.pending, (state) => {
        state.isLoading = true
      })
      .addCase(fetchDocuments.fulfilled, (state, action) => {
        state.isLoading = false
        state.documents = action.payload
      })
      .addCase(fetchDocuments.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })

    // ==================== SEND MESSAGE ====================
    builder
      .addCase(sendMessage.pending, (state) => {
        state.isSending = true
        state.error = null
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isSending = false
        if (action.payload.response) {
          state.messages.push({
            role: "assistant",
            content: action.payload.response,
            id: `ai_${Date.now()}`,
          })
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isSending = false
        state.error = action.payload
      })

    // ==================== SUBMIT FEEDBACK ====================
    builder
      .addCase(submitFeedback.pending, (state) => {
        state.isLoading = true
      })
      .addCase(submitFeedback.fulfilled, (state) => {
        state.isLoading = false
      })
      .addCase(submitFeedback.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload
      })
  },
})

export const {
  setCurrentConversationId,
  toggleSelectedDocument,
  clearSelectedDocuments,
  setSelectedDocuments,
  clearTopicSearchResults,
  clearError,
  clearMessages,
  addLocalMessage,
} = generalSlice.actions

export const generalReducer = generalSlice.reducer