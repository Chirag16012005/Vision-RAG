"use client"

import { useState } from "react"
import { useDispatch } from "react-redux"
import * as Dialog from "@radix-ui/react-dialog"
import { Star } from "lucide-react"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { submitFeedback } from "@/store/generalSlicer"


export function ChatMessages({ messages, isLoading, conversationId }) {
  const dispatch = useDispatch()
  const [activeMessageId, setActiveMessageId] = useState(null)
  const [selectedRating, setSelectedRating] = useState(0)
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)
  const [feedbackError, setFeedbackError] = useState("")

  const closeFeedback = () => {
    setActiveMessageId(null)
    setSelectedRating(0)
    setIsSubmittingFeedback(false)
    setFeedbackError("")
  }

  const handleSubmitFeedback = async () => {
    if (!conversationId || !activeMessageId || selectedRating === 0) {
      return
    }

    setIsSubmittingFeedback(true)
    setFeedbackError("")

    try {
      await dispatch(
        submitFeedback({
          conversationId,
          messageId: activeMessageId,
          rating: selectedRating,
        }),
      ).unwrap()
      closeFeedback()
    } catch (error) {
      const fallbackMessage = typeof error === "string" ? error : error?.detail || "Unable to submit feedback."
      setFeedbackError(fallbackMessage)
      setIsSubmittingFeedback(false)
    }
  }

  const renderRatingStars = () => (
    <div className="flex items-center gap-2">
      {[1, 2, 3, 4, 5].map((value) => {
        const isActive = value <= selectedRating
        return (
          <button
            key={value}
            type="button"
            className="rounded-md p-1 transition-colors hover:bg-slate-100"
            onClick={() => setSelectedRating(value)}
            aria-label={`Rate ${value} star${value > 1 ? "s" : ""}`}
          >
            <Star
              className={`size-6 ${
                isActive ? "fill-amber-400 stroke-amber-400" : "stroke-slate-400"
              }`}
              strokeWidth={1.5}
            />
          </button>
        )
      })}
    </div>
  )

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
                  {!isUser && msg.id && conversationId && (
                    <Dialog.Root
                      open={activeMessageId === msg.id}
                      onOpenChange={(open) => {
                        if (open) {
                          setActiveMessageId(msg.id)
                          setSelectedRating(0)
                          setFeedbackError("")
                        } else {
                          closeFeedback()
                        }
                      }}
                    >
                      <Dialog.Trigger asChild>
                        <Button size="sm" variant="outline" className="text-xs">
                          Give Feedback
                        </Button>
                      </Dialog.Trigger>
                      <Dialog.Portal>
                        <Dialog.Overlay className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm" />
                        <Dialog.Content className="fixed left-1/2 top-1/2 w-[min(90vw,24rem)] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl focus:outline-none">
                          <Dialog.Title className="text-lg font-semibold text-slate-900">Rate this answer</Dialog.Title>
                          <Dialog.Description className="mt-1 text-sm text-slate-600">
                            How helpful was this response?
                          </Dialog.Description>
                          <div className="mt-4">{renderRatingStars()}</div>
                          {feedbackError && (
                            <p className="mt-3 text-sm text-red-600">{feedbackError}</p>
                          )}
                          <div className="mt-6 flex justify-end gap-2">
                            <Button
                              type="button"
                              variant="ghost"
                              onClick={closeFeedback}
                              disabled={isSubmittingFeedback}
                            >
                              Cancel
                            </Button>
                            <Button
                              type="button"
                              onClick={handleSubmitFeedback}
                              disabled={selectedRating === 0 || isSubmittingFeedback}
                              className="bg-sky-500 text-white hover:bg-sky-600"
                            >
                              {isSubmittingFeedback ? "Submitting..." : "Submit"}
                            </Button>
                          </div>
                        </Dialog.Content>
                      </Dialog.Portal>
                    </Dialog.Root>
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
