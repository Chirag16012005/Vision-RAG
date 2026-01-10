"use client"

import { useState } from "react"
import { useDispatch, useSelector } from "react-redux"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ingestUrl, fetchDocuments } from "@/store/generalSlicer"

export function UrlIngestion({ conversationId }) {
  const [url, setUrl] = useState("")
  const dispatch = useDispatch()
  const { isLoading } = useSelector((state) => state.general)

  const handleProcess = async () => {
    if (!url.trim() || !conversationId) return

    await dispatch(ingestUrl({ url, conversationId }))
    setUrl("")
    dispatch(fetchDocuments(conversationId))
  }

  return (
    <div className="space-y-4">
      <Input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Enter YouTube or Website URL"
        disabled={isLoading}
        className="bg-white"
      />
      <Button
        onClick={handleProcess}
        disabled={!url.trim() || isLoading}
        className="w-full bg-sky-500 hover:bg-sky-600 text-white"
      >
        {isLoading ? "Scraping URL..." : "Process URL"}
      </Button>
    </div>
  )
}
