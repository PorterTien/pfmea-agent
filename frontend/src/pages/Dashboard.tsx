import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import PdfUpload from '../components/PdfUpload'
import { uploadPDF, startAnalysis, getAnalyses, Analysis, UploadResponse } from '../services/api'

export default function Dashboard() {
  const navigate = useNavigate()
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAnalyses()
  }, [])

  const loadAnalyses = async () => {
    try {
      setLoading(true)
      const data = await getAnalyses()
      setAnalyses(data)
    } catch (err: any) {
      if (err.response?.status === 500) {
        setError('Backend server error. Please check if the backend is running on http://localhost:8000')
      } else if (err.code === 'ECONNREFUSED' || err.message?.includes('Failed to fetch')) {
        setError('Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000')
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load analyses')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleUploadSuccess = async (response: UploadResponse) => {
    setError(null)
    // Start analysis automatically
    try {
      await startAnalysis(response.analysis_id)
      // Navigate to analysis page
      navigate(`/analysis/${response.analysis_id}`)
    } catch (err: any) {
      setError(err.message || 'Failed to start analysis')
    }
  }

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      default:
        return <FileText className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'processing':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">PFMEA Analysis Tool</h1>
          <p className="text-gray-600">Upload work instruction PDFs to generate Process Failure Mode and Effects Analysis</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload PDF</h2>
          <PdfUpload onUploadSuccess={handleUploadSuccess} onError={handleUploadError} />
        </div>

        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Analyses</h2>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : analyses.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              No analyses yet. Upload a PDF to get started.
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Filename
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Uploaded
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {analyses.map((analysis) => (
                    <tr key={analysis.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <FileText className="w-5 h-5 text-gray-400 mr-2" />
                          <span className="text-sm font-medium text-gray-900">{analysis.filename}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(analysis.status)}
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(analysis.status)}`}>
                            {analysis.status.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(analysis.uploaded_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => navigate(`/analysis/${analysis.id}`)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

