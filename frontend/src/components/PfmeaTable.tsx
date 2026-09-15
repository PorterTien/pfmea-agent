import { useState } from 'react'
import { ChevronDown, ChevronUp, AlertCircle, CheckCircle, HelpCircle } from 'lucide-react'
import { PFMEAResult } from '../services/api'

interface PfmeaTableProps {
  results: PFMEAResult[]
}

export default function PfmeaTable({ results }: PfmeaTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [sortConfig, setSortConfig] = useState<{ key: keyof PFMEAResult; direction: 'asc' | 'desc' } | null>(null)

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedRows(newExpanded)
  }

  const handleSort = (key: keyof PFMEAResult) => {
    let direction: 'asc' | 'desc' = 'asc'
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc'
    }
    setSortConfig({ key, direction })
  }

  const sortedResults = [...results].sort((a, b) => {
    if (!sortConfig) return 0
    
    const aVal = a[sortConfig.key]
    const bVal = b[sortConfig.key]
    
    if (aVal === undefined || aVal === null) return 1
    if (bVal === undefined || bVal === null) return -1
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal
    }
    
    const aStr = String(aVal).toLowerCase()
    const bStr = String(bVal).toLowerCase()
    
    if (sortConfig.direction === 'asc') {
      return aStr < bStr ? -1 : aStr > bStr ? 1 : 0
    } else {
      return aStr > bStr ? -1 : aStr < bStr ? 1 : 0
    }
  })

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'high':
        return <AlertCircle className="w-5 h-5 text-risk-high" />
      case 'medium':
        return <HelpCircle className="w-5 h-5 text-risk-medium" />
      case 'low':
        return <CheckCircle className="w-5 h-5 text-risk-low" />
      default:
        return null
    }
  }

  const getRiskBadgeColor = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getActionBadgeColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'yes':
        return 'bg-red-100 text-red-800'
      case 'maybe':
        return 'bg-yellow-100 text-yellow-800'
      case 'no':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="overflow-x-auto shadow-sm rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              ID
            </th>
            <th 
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('process')}
            >
              Process
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Failure Mode
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Effect
            </th>
            <th 
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('severity')}
            >
              S
            </th>
            <th 
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('occurrence')}
            >
              O
            </th>
            <th 
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('detection')}
            >
              D
            </th>
            <th 
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              onClick={() => handleSort('rpn')}
            >
              RPN
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Risk Level
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Action
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Details
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedResults.map((result, index) => {
            const isExpanded = expandedRows.has(index)
            return (
              <>
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {index + 1}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    <div>
                      <div className="font-medium">{result.process}</div>
                      {result.subprocess && (
                        <div className="text-xs text-gray-500 mt-1">{result.subprocess.substring(0, 50)}...</div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 max-w-xs">
                    <div className="truncate" title={result.failure_mode}>
                      {result.failure_mode}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 max-w-xs">
                    <div className="truncate" title={result.potential_effect}>
                      {result.potential_effect}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    {result.severity}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    {result.occurrence}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    {result.detection}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-bold text-gray-900">
                    {result.rpn}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getRiskBadgeColor(result.risk_level)}`}>
                      {getRiskIcon(result.risk_level)}
                      {result.risk_level.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getActionBadgeColor(result.action_required)}`}>
                      {result.action_required.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm">
                    <button
                      onClick={() => toggleRow(index)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5" />
                      ) : (
                        <ChevronDown className="w-5 h-5" />
                      )}
                    </button>
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={11} className="px-4 py-4 bg-gray-50">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-semibold text-sm text-gray-700 mb-2">Severity Justification</h4>
                          <p className="text-sm text-gray-600 whitespace-pre-wrap">{result.severity_justification || 'N/A'}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm text-gray-700 mb-2">Occurrence Justification</h4>
                          <p className="text-sm text-gray-600 whitespace-pre-wrap">{result.occurrence_justification || 'N/A'}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm text-gray-700 mb-2">Detection Justification</h4>
                          <p className="text-sm text-gray-600 whitespace-pre-wrap">{result.detection_justification || 'N/A'}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-sm text-gray-700 mb-2">Additional Info</h4>
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Control Point:</span> {result.control_point || 'N/A'}<br />
                            <span className="font-medium">Confidence:</span> {result.confidence || 'N/A'}
                          </p>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
      {results.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No PFMEA results available
        </div>
      )}
    </div>
  )
}




