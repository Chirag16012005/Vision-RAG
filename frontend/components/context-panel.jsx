"use client"

import { useDispatch, useSelector } from "react-redux"
import { toggleSelectedDocument } from "@/store/generalSlicer"

export function ContextPanel() {
  const dispatch = useDispatch()
  const { documents, selectedDocuments } = useSelector((state) => state.general)

  const handleToggleDocument = (docName) => {
    dispatch(toggleSelectedDocument(docName))
  }

  return (
    <div className="w-64 bg-white/92 border-l border-slate-200 p-5 flex flex-col shadow-lg">
      <h2 className="text-lg font-semibold text-slate-900 mb-4">📂 Context</h2>

      <div className="flex-1 overflow-y-auto space-y-2">
        {documents.length === 0 ? (
          <p className="text-sm text-slate-500 bg-blue-50 p-3 rounded-lg">No documents linked to this chat.</p>
        ) : (
          documents.map((doc) => (
            <label
              key={doc}
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedDocuments.includes(doc)}
                onChange={() => handleToggleDocument(doc)}
                className="w-4 h-4 rounded border-slate-300 text-sky-500 focus:ring-sky-500"
              />
              <span className="text-sm text-slate-700 truncate">{doc}</span>
            </label>
          ))
        )}
      </div>
    </div>
  )
}
