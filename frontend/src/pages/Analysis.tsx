import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Loader2, AlertCircle, RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import PfmeaTable from '../components/PfmeaTable'
import { getAnalysis, getAnalysisStatus, exportResults, AnalysisWithResults, PFMEAResult } from '../services/api'
import { useWebSocket, WebSocketMessage } from '../hooks/useWebSocket'

export default function Analysis() {
  const { analysisId } = useParams<{ analysisId: string }>()
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState<AnalysisWithResults | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)
  const [progressLog, setProgressLog] = useState<WebSocketMessage[]>([])
  const [currentStep, setCurrentStep] = useState<string>('')
  const [wsLogs, setWsLogs] = useState<Array<{time: string, type: string, message: string, data?: any}>>([])
  const [showWsLogs, setShowWsLogs] = useState(true)

  useEffect(() => {
    if (analysisId) {
      loadAnalysis()
    }
  }, [analysisId])

  // WebSocket connection for real-time updates
  const { isConnected, messages } = useWebSocket(
    analysisId ? parseInt(analysisId) : null,
    (message: WebSocketMessage) => {
      const timestamp = new Date().toLocaleTimeString()
      
      // Add to WebSocket logs
      setWsLogs((prev) => [...prev, {
        time: timestamp,
        type: 'message',
        message: `Received: ${message.type || 'update'}`,
        data: message
      }])
      
      setProgressLog((prev) => [...prev, message])
      
      // Update current step
      if (message.step) {
        setCurrentStep(message.step)
      }
      
      // If analysis completed, reload the analysis
      if (message.step === 'complete' && message.status === 'completed') {
        setTimeout(() => {
          loadAnalysis()
        }, 1000)
      }
      
      // If error occurred, update error state
      if (message.step === 'error' && message.status === 'failed') {
        setError(message.message || 'Analysis failed')
      }
    },
    (logEntry: {time: string, type: string, message: string, data?: any}) => {
      setWsLogs((prev) => [...prev, logEntry])
    }
  )

  useEffect(() => {
    if (analysis?.status === 'processing') {
      setPolling(true)
      const interval = setInterval(() => {
        checkStatus()
      }, 5000) // Poll every 5 seconds (WebSocket handles real-time updates)

      return () => {
        clearInterval(interval)
        setPolling(false)
      }
    } else {
      setPolling(false)
    }
  }, [analysis?.status])

  const loadAnalysis = async () => {
    if (!analysisId) return
    
    try {
      setLoading(true)
      const data = await getAnalysis(parseInt(analysisId))
      setAnalysis(data)
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to load analysis')
    } finally {
      setLoading(false)
    }
  }

  const checkStatus = async () => {
    if (!analysisId) return
    
    try {
      const status = await getAnalysisStatus(parseInt(analysisId))
      if (status.status !== 'processing') {
        // Reload full analysis when status changes
        await loadAnalysis()
      }
    } catch (err) {
      console.error('Failed to check status:', err)
    }
  }

  const handleExport = async (format: 'csv' | 'excel') => {
    if (!analysisId) return
    
    try {
      const blob = await exportResults(parseInt(analysisId), format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pfmea_analysis_${analysisId}.${format === 'csv' ? 'csv' : 'xlsx'}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      setError(err.message || 'Export failed')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  if (error && !analysis) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-800"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </button>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{analysis.filename}</h1>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>Uploaded: {new Date(analysis.uploaded_at).toLocaleString()}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                  analysis.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {analysis.status.toUpperCase()}
                </span>
                {polling && (
                  <span className="flex items-center gap-2 text-blue-600">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Processing...
                  </span>
                )}
              </div>
            </div>
            
            {analysis.status === 'completed' && analysis.pfmea_results.length > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport('csv')}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </button>
                <button
                  onClick={() => handleExport('excel')}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  <Download className="w-4 h-4" />
                  Export Excel
                </button>
              </div>
            )}
          </div>
        </div>

        {analysis.error_message && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            <strong>Error:</strong> {analysis.error_message}
          </div>
        )}

        {analysis.status === 'processing' && (
          <div className="mb-6 space-y-4">
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg">
              <div className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>
                  Analysis in progress{currentStep ? `: ${currentStep}` : ''}
                  {isConnected && (
                    <span className="ml-2 text-xs">(Live updates connected)</span>
                  )}
                </span>
              </div>
            </div>
            
            {/* WebSocket Connection Log */}
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 max-h-64 overflow-y-auto mb-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                  <span>WebSocket Logs</span>
                  {isConnected ? (
                    <span className="text-xs text-green-400 flex items-center gap-1">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      Connected
                    </span>
                  ) : analysis?.status === 'processing' ? (
                    <span className="text-xs text-yellow-400 flex items-center gap-1">
                      <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                      Connecting...
                    </span>
                  ) : (
                    <span className="text-xs text-red-400 flex items-center gap-1">
                      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                      Disconnected
                    </span>
                  )}
                </h3>
                <button
                  onClick={() => setShowWsLogs(!showWsLogs)}
                  className="text-xs text-gray-400 hover:text-gray-200"
                >
                  {showWsLogs ? 'Hide' : 'Show'}
                </button>
              </div>
              {showWsLogs && (
                <div className="space-y-1 font-mono text-xs">
                  {wsLogs.length === 0 ? (
                    <div className="text-gray-500 italic">No WebSocket activity yet...</div>
                  ) : (
                    wsLogs.slice(-50).map((log, idx) => (
                      <div
                        key={idx}
                        className={`p-2 rounded ${
                          log.type === 'error' ? 'bg-red-900/30 text-red-300' :
                          log.type === 'connect' ? 'bg-green-900/30 text-green-300' :
                          log.type === 'disconnect' ? 'bg-yellow-900/30 text-yellow-300' :
                          log.type === 'message' ? 'bg-blue-900/30 text-blue-300' :
                          'bg-gray-800 text-gray-300'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <span className="text-gray-500 flex-shrink-0">[{log.time}]</span>
                          <span className="font-semibold flex-shrink-0">{log.type.toUpperCase()}:</span>
                          <span className="flex-1">{log.message}</span>
                        </div>
                        {log.data && (
                          <details className="mt-1 ml-8">
                            <summary className="cursor-pointer text-gray-400 hover:text-gray-200 text-xs">
                              View data
                            </summary>
                            <pre className="mt-1 text-xs overflow-x-auto bg-black/50 p-2 rounded">
                              {JSON.stringify(log.data, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Progress Log */}
            {progressLog.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-lg p-4 max-h-96 overflow-y-auto">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <span>Analysis Progress</span>
                  {isConnected ? (
                    <span className="text-xs text-green-600 flex items-center gap-1">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      Live
                    </span>
                  ) : analysis?.status === 'processing' ? (
                    <span className="text-xs text-yellow-600 flex items-center gap-1">
                      <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                      Connecting...
                    </span>
                  ) : (
                    <span className="text-xs text-gray-500">Disconnected</span>
                  )}
                </h3>
                <div className="space-y-2">
                  {progressLog.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`text-sm p-2 rounded ${
                        msg.status === 'completed' || msg.status === 'started'
                          ? 'bg-green-50 text-green-800'
                          : msg.status === 'error' || msg.status === 'failed'
                          ? 'bg-red-50 text-red-800'
                          : 'bg-gray-50 text-gray-700'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {msg.status === 'completed' && (
                          <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        {msg.status === 'error' || msg.status === 'failed' && (
                          <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        )}
                        {msg.status === 'started' && (
                          <Loader2 className="w-4 h-4 mt-0.5 animate-spin flex-shrink-0" />
                        )}
                        <div className="flex-1">
                          <div className="font-medium">{msg.message || 'Processing...'}</div>
                          {msg.reasoning && (
                            <div className="text-xs mt-1 opacity-75 italic">
                              {msg.reasoning.substring(0, 200)}
                              {msg.reasoning.length > 200 ? '...' : ''}
                            </div>
                          )}
                          {msg.ratings && (
                            <div className="text-xs mt-1">
                              Ratings: S={msg.ratings.severity}, O={msg.ratings.occurrence}, D={msg.ratings.detection}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {analysis.status === 'completed' && analysis.pfmea_results.length > 0 && (
          <div className="mb-4">
            <div className="bg-white rounded-lg shadow p-4 mb-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">Summary</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Total Results</div>
                  <div className="text-2xl font-bold text-gray-900">{analysis.pfmea_results.length}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">High Risk</div>
                  <div className="text-2xl font-bold text-red-600">
                    {analysis.pfmea_results.filter(r => r.risk_level.toLowerCase() === 'high').length}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Medium Risk</div>
                  <div className="text-2xl font-bold text-yellow-600">
                    {analysis.pfmea_results.filter(r => r.risk_level.toLowerCase() === 'medium').length}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Low Risk</div>
                  <div className="text-2xl font-bold text-green-600">
                    {analysis.pfmea_results.filter(r => r.risk_level.toLowerCase() === 'low').length}
                  </div>
                </div>
              </div>
            </div>
            
            <PfmeaTable results={analysis.pfmea_results} />
          </div>
        )}

        {analysis.status === 'completed' && analysis.pfmea_results.length === 0 && (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
            No PFMEA results found for this analysis.
          </div>
        )}
      </div>
    </div>
  )
}

