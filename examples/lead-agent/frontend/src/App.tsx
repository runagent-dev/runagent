import React, { useState } from 'react';
import { Upload, FileText, Mail, CheckCircle, AlertCircle, Loader2, ArrowRight, ArrowLeft } from 'lucide-react';
import Papa from 'papaparse';

interface Candidate {
  id: string;
  name: string;
  email: string;
  bio: string;
  skills: string;
}

interface ScoredCandidate extends Candidate {
  score: number;
  reason: string;
}

interface EmailGenerated {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  proceed_with_candidate: boolean;
  email_content: string;
}

interface FlowResult {
  success: boolean;
  total_candidates: number;
  top_candidates: ScoredCandidate[];
  all_candidates: ScoredCandidate[];
  emails_generated?: EmailGenerated[];
  error?: string;
}

interface CSVMapping {
  id: string;
  name: string;
  email: string;
  bio: string;
  skills: string;
}

function App() {
  const [step, setStep] = useState<'config' | 'upload' | 'mapping' | 'processing' | 'results'>('config');
  const [jobDescription, setJobDescription] = useState('');
  const [topN, setTopN] = useState(3);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [results, setResults] = useState<FlowResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // CSV mapping state
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvData, setCsvData] = useState<any[]>([]);
  const [columnMapping, setColumnMapping] = useState<CSVMapping>({
    id: '',
    name: '',
    email: '',
    bio: '',
    skills: ''
  });

  // Smart column detection
  const detectColumn = (header: string, targetField: string): boolean => {
    const headerLower = header.toLowerCase();
    const patterns: Record<string, string[]> = {
      id: ['id', 'candidate_id', 'applicant_id', 'number', '#'],
      name: ['name', 'full_name', 'fullname', 'candidate_name', 'applicant_name', 'first_name'],
      email: ['email', 'e-mail', 'mail', 'email_address', 'contact'],
      bio: ['bio', 'biography', 'description', 'about', 'summary', 'profile', 'experience', 'background'],
      skills: ['skills', 'skill', 'expertise', 'technologies', 'tech_stack', 'competencies']
    };
    
    return patterns[targetField]?.some(pattern => headerLower.includes(pattern)) || false;
  };

  const autoMapColumns = (headers: string[]) => {
    const mapping: CSVMapping = {
      id: '',
      name: '',
      email: '',
      bio: '',
      skills: ''
    };

    headers.forEach(header => {
      Object.keys(mapping).forEach(field => {
        if (!mapping[field as keyof CSVMapping] && detectColumn(header, field)) {
          mapping[field as keyof CSVMapping] = header;
        }
      });
    });

    // If no ID column found, we'll generate IDs
    if (!mapping.id && headers.length > 0) {
      mapping.id = '_auto_generate_';
    }

    setColumnMapping(mapping);
  };

  const handleFileUpload = (file: File) => {
    setError(null);
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        if (results.data.length === 0) {
          setError('CSV file is empty');
          return;
        }

        const headers = Object.keys(results.data[0] as object);
        setCsvHeaders(headers);
        setCsvData(results.data);
        
        // Auto-detect columns
        autoMapColumns(headers);
        
        setStep('mapping');
      },
      error: (error) => {
        setError(`Error parsing CSV: ${error.message}`);
      }
    });
  };

  const mapAndProcessCandidates = () => {
    // Validate required mappings
    if (!columnMapping.name) {
      setError('Please map the "Name" column');
      return;
    }

    const mappedCandidates: Candidate[] = csvData.map((row, index) => {
      return {
        id: columnMapping.id === '_auto_generate_' 
          ? `candidate_${index + 1}` 
          : (row[columnMapping.id] || `candidate_${index + 1}`),
        name: row[columnMapping.name] || 'Unknown',
        email: columnMapping.email ? (row[columnMapping.email] || '') : '',
        bio: columnMapping.bio ? (row[columnMapping.bio] || '') : '',
        skills: columnMapping.skills ? (row[columnMapping.skills] || '') : ''
      };
    }).filter(candidate => candidate.name && candidate.name !== 'Unknown');

    if (mappedCandidates.length === 0) {
      setError('No valid candidates found after mapping');
      return;
    }

    setCandidates(mappedCandidates);
    setStep('processing');
    runLeadScoring(mappedCandidates);
  };

  const runLeadScoring = async (candidateList: Candidate[]) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/score-leads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          candidates: candidateList,
          job_description: jobDescription,
          top_n: topN,
          generate_emails: true
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to score leads');
      }

      const result: FlowResult = await response.json();
      
      // Debug: Log the response
      console.log('Response received:', result);
      
      // Validate response structure
      if (!result || typeof result !== 'object') {
        throw new Error('Invalid response format');
      }
      
      // Check if response has error
      if ('error' in result && result.error) {
        throw new Error(result.error);
      }
      
      // Ensure required fields exist
      if (result.success === false || (!result.total_candidates && !result.top_candidates)) {
        throw new Error('Response missing required fields or operation failed');
      }
      
      setResults(result);
      setStep('results');
    } catch (err) {
      console.error('Error in runLeadScoring:', err);
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      console.error('Error details:', {
        message: errorMessage,
        error: err,
        stack: err instanceof Error ? err.stack : undefined
      });
      setError(errorMessage);
      setStep('mapping'); // Go back to mapping on error
    } finally {
      setLoading(false);
    }
  };

  const downloadEmails = () => {
    if (!results?.emails_generated) return;

    results.emails_generated.forEach((email) => {
      const blob = new Blob([email.email_content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${email.candidate_name.replace(/\s+/g, '_')}_email.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  };

  const downloadCSV = () => {
    if (!results?.all_candidates) return;

    const csv = Papa.unparse(results.all_candidates.map(c => ({
      id: c.id,
      name: c.name,
      email: c.email,
      score: c.score,
      reason: c.reason
    })));

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'lead_scores.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getMappingStatus = () => {
    const required = ['name'];
    const optional = ['email', 'bio', 'skills'];
    const requiredMapped = required.every(field => columnMapping[field as keyof CSVMapping]);
    const optionalMapped = optional.filter(field => columnMapping[field as keyof CSVMapping]).length;
    
    return { requiredMapped, optionalMapped, totalOptional: optional.length };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            AI Lead Scoring System
          </h1>
          <p className="text-gray-600">Powered by RunAgent & CrewAI</p>
        </div>

        {/* Configuration Step */}
        {step === 'config' && (
          <div className="bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-2xl font-semibold mb-6 flex items-center">
              <FileText className="mr-2" />
              Configuration
            </h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Job Description *
                </label>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the job description here..."
                  rows={8}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Top Candidates
                </label>
                <input
                  type="number"
                  value={topN}
                  onChange={(e) => setTopN(parseInt(e.target.value))}
                  min="1"
                  max="10"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <button
                onClick={() => setStep('upload')}
                disabled={!jobDescription}
                className="w-full bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors flex items-center justify-center"
              >
                Continue to Upload Candidates
                <ArrowRight className="ml-2 h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {/* Upload Step */}
        {step === 'upload' && (
          <div className="bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-2xl font-semibold mb-6 flex items-center">
              <Upload className="mr-2" />
              Upload Candidates CSV
            </h2>

            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800 font-medium mb-2">✨ Flexible CSV Upload</p>
              <p className="text-sm text-blue-700">
                Upload any CSV format! We'll help you map columns in the next step.
                Your CSV should contain candidate information like names, emails, bios, and skills.
              </p>
            </div>

            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-500 transition-colors cursor-pointer"
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file && file.type === 'text/csv') {
                  handleFileUpload(file);
                } else {
                  setError('Please upload a CSV file');
                }
              }}
              onDragOver={(e) => e.preventDefault()}
            >
              <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <p className="text-lg text-gray-600 mb-2">
                Drop your CSV file here, or click to select
              </p>
              <p className="text-sm text-gray-500 mb-4">
                Any CSV format accepted - we'll help you map the columns
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                }}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-block bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 cursor-pointer"
              >
                Select CSV File
              </label>
            </div>

            <button
              onClick={() => setStep('config')}
              className="mt-6 text-gray-600 hover:text-gray-900 flex items-center"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Configuration
            </button>
          </div>
        )}

        {/* Column Mapping Step */}
        {step === 'mapping' && (
          <div className="bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-2xl font-semibold mb-6">
              Map Your CSV Columns
            </h2>

            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-800">
                ✅ CSV loaded with {csvData.length} rows and {csvHeaders.length} columns
              </p>
              <p className="text-sm text-green-700 mt-1">
                We've auto-detected some columns. Please verify and adjust if needed.
              </p>
            </div>

            <div className="space-y-4 mb-6">
              {/* ID Mapping */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ID Column <span className="text-gray-500">(optional - we'll generate if needed)</span>
                </label>
                <select
                  value={columnMapping.id}
                  onChange={(e) => setColumnMapping({ ...columnMapping, id: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="_auto_generate_">Auto-generate IDs</option>
                  {csvHeaders.map(header => (
                    <option key={header} value={header}>{header}</option>
                  ))}
                </select>
              </div>

              {/* Name Mapping */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Name Column * <span className="text-red-500">(required)</span>
                </label>
                <select
                  value={columnMapping.name}
                  onChange={(e) => setColumnMapping({ ...columnMapping, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Select Name Column --</option>
                  {csvHeaders.map(header => (
                    <option key={header} value={header}>{header}</option>
                  ))}
                </select>
              </div>

              {/* Email Mapping */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Column <span className="text-gray-500">(optional but recommended)</span>
                </label>
                <select
                  value={columnMapping.email}
                  onChange={(e) => setColumnMapping({ ...columnMapping, email: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Skip this column --</option>
                  {csvHeaders.map(header => (
                    <option key={header} value={header}>{header}</option>
                  ))}
                </select>
              </div>

              {/* Bio Mapping */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Bio/Description Column <span className="text-gray-500">(optional but recommended)</span>
                </label>
                <select
                  value={columnMapping.bio}
                  onChange={(e) => setColumnMapping({ ...columnMapping, bio: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Skip this column --</option>
                  {csvHeaders.map(header => (
                    <option key={header} value={header}>{header}</option>
                  ))}
                </select>
              </div>

              {/* Skills Mapping */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Skills Column <span className="text-gray-500">(optional but recommended)</span>
                </label>
                <select
                  value={columnMapping.skills}
                  onChange={(e) => setColumnMapping({ ...columnMapping, skills: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Skip this column --</option>
                  {csvHeaders.map(header => (
                    <option key={header} value={header}>{header}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Preview */}
            <div className="mb-6 bg-gray-50 rounded-lg p-4">
              <h3 className="font-medium text-gray-900 mb-2">Preview (first 3 rows)</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="px-2 py-1 text-left">ID</th>
                      <th className="px-2 py-1 text-left">Name</th>
                      <th className="px-2 py-1 text-left">Email</th>
                      <th className="px-2 py-1 text-left">Bio</th>
                      <th className="px-2 py-1 text-left">Skills</th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvData.slice(0, 3).map((row, idx) => (
                      <tr key={idx} className="border-b">
                        <td className="px-2 py-1">
                          {columnMapping.id === '_auto_generate_' ? `candidate_${idx + 1}` : (row[columnMapping.id] || '-')}
                        </td>
                        <td className="px-2 py-1">{row[columnMapping.name] || '-'}</td>
                        <td className="px-2 py-1">{row[columnMapping.email] || '-'}</td>
                        <td className="px-2 py-1 truncate max-w-xs">{row[columnMapping.bio] || '-'}</td>
                        <td className="px-2 py-1">{row[columnMapping.skills] || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => setStep('upload')}
                className="flex-1 bg-gray-600 text-white py-3 rounded-md hover:bg-gray-700 font-medium flex items-center justify-center"
              >
                <ArrowLeft className="mr-2 h-5 w-5" />
                Back
              </button>
              <button
                onClick={mapAndProcessCandidates}
                disabled={!columnMapping.name}
                className="flex-1 bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium flex items-center justify-center"
              >
                Process Candidates
                <ArrowRight className="ml-2 h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {/* Processing Step */}
        {step === 'processing' && (
          <div className="bg-white rounded-lg shadow-xl p-8 text-center">
            <Loader2 className="mx-auto h-16 w-16 text-blue-600 animate-spin mb-4" />
            <h2 className="text-2xl font-semibold mb-2">Processing Candidates</h2>
            <p className="text-gray-600 mb-4">
              AI agents are analyzing {candidates.length} candidates...
            </p>
            <p className="text-sm text-gray-500">
              This may take a few minutes depending on the number of candidates
            </p>
          </div>
        )}

        {/* Results Step */}
        {step === 'results' && results && (
          <div className="space-y-6">
            {/* Summary Card */}
            <div className="bg-white rounded-lg shadow-xl p-8">
              <h2 className="text-2xl font-semibold mb-6 flex items-center">
                <CheckCircle className="mr-2 text-green-600" />
                Scoring Complete!
              </h2>

              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Total Candidates</p>
                  <p className="text-3xl font-bold text-blue-600">
                    {results.total_candidates}
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Top Candidates</p>
                  <p className="text-3xl font-bold text-green-600">
                    {results.top_candidates.length}
                  </p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Emails Generated</p>
                  <p className="text-3xl font-bold text-purple-600">
                    {results.emails_generated?.length || 0}
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={downloadCSV}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 font-medium"
                >
                  Download Scores CSV
                </button>
                <button
                  onClick={downloadEmails}
                  className="flex-1 bg-green-600 text-white py-2 rounded-md hover:bg-green-700 font-medium"
                >
                  Download All Emails
                </button>
              </div>
            </div>

            {/* Top Candidates */}
            <div className="bg-white rounded-lg shadow-xl p-8">
              <h3 className="text-xl font-semibold mb-4">Top {topN} Candidates</h3>
              <div className="space-y-4">
                {results.top_candidates.map((candidate, index) => (
                  <div
                    key={candidate.id}
                    className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center">
                        <span className="bg-blue-600 text-white font-bold px-3 py-1 rounded-full mr-3">
                          #{index + 1}
                        </span>
                        <div>
                          <h4 className="font-semibold text-lg">{candidate.name}</h4>
                          <p className="text-sm text-gray-600">{candidate.email}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-blue-600">
                          {candidate.score}
                        </div>
                        <p className="text-xs text-gray-500">Score</p>
                      </div>
                    </div>
                    {candidate.skills && (
                      <div className="mt-3">
                        <p className="text-sm font-medium text-gray-700 mb-1">Skills:</p>
                        <p className="text-sm text-gray-600">{candidate.skills}</p>
                      </div>
                    )}
                    <div className="mt-3 bg-gray-50 p-3 rounded">
                      <p className="text-sm font-medium text-gray-700 mb-1">Analysis:</p>
                      <p className="text-sm text-gray-600">{candidate.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* All Candidates Summary */}
            <div className="bg-white rounded-lg shadow-xl p-8">
              <h3 className="text-xl font-semibold mb-4">All Candidates</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Rank
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Name
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Email
                      </th>
                      <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">
                        Score
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {results.all_candidates.map((candidate, index) => (
                      <tr
                        key={candidate.id}
                        className={index < topN ? 'bg-green-50' : ''}
                      >
                        <td className="px-4 py-2 text-sm">{index + 1}</td>
                        <td className="px-4 py-2 text-sm font-medium">
                          {candidate.name}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-600">
                          {candidate.email}
                        </td>
                        <td className="px-4 py-2 text-sm">
                          <span
                            className={`font-bold ${
                              index < topN ? 'text-green-600' : 'text-gray-600'
                            }`}
                          >
                            {candidate.score}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <button
              onClick={() => {
                setStep('config');
                setResults(null);
                setCandidates([]);
                setCsvData([]);
                setCsvHeaders([]);
              }}
              className="w-full bg-gray-600 text-white py-3 rounded-md hover:bg-gray-700 font-medium"
            >
              Start New Scoring Session
            </button>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start mt-6">
            <AlertCircle className="text-red-600 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-red-900">Error</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;