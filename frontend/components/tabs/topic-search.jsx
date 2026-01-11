"use client"

import { useState } from "react"
import { useDispatch, useSelector } from "react-redux"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { searchTopic, ingestTopic, clearTopicSearchResults, fetchDocuments } from "@/store/generalSlicer"

export function TopicSearch({ conversationId }) {
  const [topic, setTopic] = useState("")
  const [selectedUrls, setSelectedUrls] = useState(new Set())
  const dispatch = useDispatch()
  const { topicSearchResults, isSearching, isLoading } = useSelector((state) => state.general)

  const handleSearch = async () => {
    if (!topic.trim()) return
    dispatch(searchTopic({ topic, seenUrls: [] }))
  }

  const handleIngestSelected = async () => {
    if (selectedUrls.size === 0 || !conversationId) return

    await dispatch(ingestTopic({ topic, conversationId, selectedUrls }))
    setSelectedUrls(new Set())
    setTopic("")
    dispatch(clearTopicSearchResults())
    dispatch(fetchDocuments(conversationId))
  }

  if (topicSearchResults.length === 0) {
    return (
      <div className="space-y-4">
        <Input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter a topic (e.g., 'Latest AI News')"
          disabled={isSearching}
          className="bg-white"
        />
        <Button
          onClick={handleSearch}
          disabled={!topic.trim() || isSearching}
          className="w-full bg-sky-500 hover:bg-sky-600 text-white"
        >
          {isSearching ? "Searching..." : "Search Topic"}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Results for: <strong>{topic}</strong>
      </p>

      <div className="space-y-3">
        {topicSearchResults.map((result) => (
          <label
            key={result.url}
            className="flex items-start gap-3 p-3 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
          >
            <Checkbox
              checked={selectedUrls.has(result.url)}
              onCheckedChange={(checked) => {
                const newSelected = new Set(selectedUrls)
                if (checked) {
                  newSelected.add(result.url)
                } else {
                  newSelected.delete(result.url)
                }
                setSelectedUrls(newSelected)
              }}
              className="mt-1"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900">{result.title}</p>
              <p className="text-xs text-slate-500 truncate">{result.url}</p>
            </div>
          </label>
        ))}
      </div>

      <div className="flex gap-3">
        <Button
          onClick={handleIngestSelected}
          disabled={selectedUrls.size === 0 || isLoading}
          className="flex-1 bg-sky-500 hover:bg-sky-600 text-white"
        >
          Ingest Selected
        </Button>
        <Button onClick={() => dispatch(clearTopicSearchResults())} variant="outline" className="flex-1">
          Clear Search
        </Button>
      </div>
    </div>
  )
}
