import { useState, useCallback } from 'react'
import { Upload, File, X, Loader2 } from 'lucide-react'
import { uploadPDF, UploadResponse } from '../services/api'

interface PdfUploadProps {
  onUploadSuccess: (response: UploadResponse) => void
  onError?: (error: string) => void
}

export default function PdfUpload({ onUploadSuccess, onError }: PdfUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleFile = useCallback(async (file: File) => {
    // Validate file type
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      onError?.('Please upload a PDF file')
      return
    }

    // Validate file size (50MB)
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      onError?.('File size exceeds 50MB limit')
      return
    }

    setSelectedFile(file)
    setIsUploading(true)

    try {
      const response = await uploadPDF(file)
      onUploadSuccess(response)
      setSelectedFile(null)
    } catch (error: any) {
      onError?.(error.response?.data?.detail || 'Upload failed. Please try again.')
      setSelectedFile(null)
    } finally {
      setIsUploading(false)
    }
  }, [onUploadSuccess, onError])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      handleFile(file)
    }
  }, [handleFile])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFile(file)
    }
  }, [handleFile])

  const removeFile = useCallback(() => {
    setSelectedFile(null)
  }, [])

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-gray-400'}
        `}
      >
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileInput}
          disabled={isUploading}
          className="hidden"
          id="pdf-upload-input"
        />
        
        <label
          htmlFor="pdf-upload-input"
          className="cursor-pointer"
        >
          {isUploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
              <p className="text-gray-600">Uploading...</p>
            </div>
          ) : selectedFile ? (
            <div className="flex flex-col items-center">
              <File className="w-12 h-12 text-green-500 mb-4" />
              <p className="text-gray-700 font-medium">{selectedFile.name}</p>
              <p className="text-sm text-gray-500 mt-1">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <button
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  removeFile()
                }}
                className="mt-4 text-red-500 hover:text-red-700 flex items-center gap-2"
              >
                <X className="w-4 h-4" />
                Remove
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <Upload className="w-12 h-12 text-gray-400 mb-4" />
              <p className="text-gray-700 font-medium mb-2">
                Drag and drop your PDF here, or click to browse
              </p>
              <p className="text-sm text-gray-500">
                PDF files only (max 50MB)
              </p>
            </div>
          )}
        </label>
      </div>
    </div>
  )
}




