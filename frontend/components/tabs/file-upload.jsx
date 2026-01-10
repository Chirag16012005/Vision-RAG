"use client"

import { useState } from "react"
import { useDispatch, useSelector } from "react-redux"
import { Button } from "@/components/ui/button"
import { Upload } from "lucide-react"
import { uploadFile, fetchDocuments } from "@/store/generalSlicer"

export function FileUpload({ conversationId }) {
  const [files, setFiles] = useState([])
  const dispatch = useDispatch()
  const { isUploading } = useSelector((state) => state.general)

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files))
    }
  }

  const handleUpload = async () => {
    if (!files.length || !conversationId) return

    for (const file of files) {
      await dispatch(uploadFile({ file, conversationId }))
    }

    setFiles([])
    dispatch(fetchDocuments(conversationId))
  }

  return (
    <div className="space-y-4">
      <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center cursor-pointer hover:border-slate-400 transition-colors">
        <input
          type="file"
          multiple
          onChange={handleFileChange}
          accept=".pdf,.txt,.mp3,.wav"
          className="hidden"
          id="file-upload"
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          <div className="flex justify-center mb-2">
            <Upload className="w-8 h-8 text-slate-400" />
          </div>
          <p className="text-sm text-slate-600">
            {files.length > 0 ? `${files.length} file(s) selected` : "Drag files here or click to upload"}
          </p>
          <p className="text-xs text-slate-500 mt-1">PDF, TXT, Audio files supported</p>
        </label>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f) => (
            <div key={f.name} className="text-sm text-slate-700 bg-slate-50 p-2 rounded">
              {f.name}
            </div>
          ))}
        </div>
      )}

      <Button
        onClick={handleUpload}
        disabled={!files.length || isUploading}
        className="w-full bg-sky-500 hover:bg-sky-600 text-white"
      >
        {isUploading ? "Processing Files..." : "Process Files"}
      </Button>
    </div>
  )
}
