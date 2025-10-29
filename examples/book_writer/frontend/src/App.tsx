import React, { useState } from 'react';
import { BookOpen, FileText, Download, Loader2, ArrowRight, ArrowLeft, Sparkles, Check } from 'lucide-react';

interface Chapter {
  number: number;
  title: string;
  description?: string;
  content?: string;
  word_count?: number;
}

interface BookResult {
  success: boolean;
  title: string;
  topic: string;
  goal: string;
  book_content: string;
  chapters: Chapter[];
  total_chapters: number;
  total_words: number;
  outline: Chapter[];
  error?: string;
}

function App() {
  const [step, setStep] = useState<'config' | 'processing' | 'results'>('config');
  const [agentId, setAgentId] = useState('');
  const [bookTitle, setBookTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [goal, setGoal] = useState('');
  const [numChapters, setNumChapters] = useState(5);
  const [result, setResult] = useState<BookResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState('');

  const generateBook = async () => {
    setLoading(true);
    setError(null);
    setStep('processing');
    setProgress('Initializing book generation...');

    try {
      setProgress('Generating book outline...');
      
      const response = await fetch('http://localhost:8000/api/write-book', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          agent_id: agentId,
          title: bookTitle,
          topic: topic,
          goal: goal,
          num_chapters: numChapters
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate book');
      }

      const data: BookResult = await response.json();
      
      if (data.success) {
        setResult(data);
        setStep('results');
      } else {
        throw new Error(data.error || 'Book generation failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStep('config');
    } finally {
      setLoading(false);
    }
  };

  const downloadBook = async () => {
    if (!result) return;

    try {
      const response = await fetch('http://localhost:8000/api/download-book', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: result.title,
          content: result.book_content
        }),
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${result.title.replace(/\s+/g, '_')}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to download book');
    }
  };

  const resetForm = () => {
    setStep('config');
    setResult(null);
    setError(null);
    setProgress('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <BookOpen className="h-12 w-12 text-purple-600 mr-3" />
            <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
              AI Book Writer
            </h1>
          </div>
          <p className="text-gray-600 text-lg">
            Generate complete books with AI-powered research and writing
          </p>
          <div className="mt-3 flex items-center justify-center gap-2 text-sm text-gray-500">
            <Sparkles className="h-4 w-4 text-purple-500" />
            <span>Powered by CrewAI & RunAgent</span>
          </div>
        </div>

        {/* Configuration Step */}
        {step === 'config' && (
          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <h2 className="text-2xl font-semibold mb-6 flex items-center text-gray-800">
              <FileText className="mr-3 text-purple-600" />
              Book Configuration
            </h2>
            
            <div className="space-y-6">
              {/* Agent ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  RunAgent Agent ID *
                </label>
                <input
                  type="text"
                  value={agentId}
                  onChange={(e) => setAgentId(e.target.value)}
                  placeholder="Enter your deployed agent ID"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                />
                <p className="mt-2 text-sm text-gray-500">
                  Get this from: <code className="bg-gray-100 px-2 py-1 rounded">runagent serve .</code>
                </p>
              </div>

              {/* Book Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Book Title *
                </label>
                <input
                  type="text"
                  value={bookTitle}
                  onChange={(e) => setBookTitle(e.target.value)}
                  placeholder="e.g., The Future of AI in Healthcare"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                />
              </div>

              {/* Topic */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Topic *
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g., AI applications in medical diagnosis and treatment"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                />
              </div>

              {/* Goal */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Book Goal / Purpose *
                </label>
                <textarea
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="Describe the main goal and target audience for this book..."
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                />
              </div>

              {/* Number of Chapters */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Chapters
                </label>
                <input
                  type="number"
                  value={numChapters}
                  onChange={(e) => setNumChapters(parseInt(e.target.value))}
                  min="1"
                  max="15"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                />
                <p className="mt-2 text-sm text-gray-500">
                  Recommended: 3-8 chapters. Each chapter will be ~3,000 words.
                </p>
              </div>

              {/* Generate Button */}
              <button
                onClick={generateBook}
                disabled={!agentId || !bookTitle || !topic || !goal}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-lg hover:from-purple-700 hover:to-blue-700 disabled:from-gray-400 disabled:to-gray-400 disabled:cursor-not-allowed font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center"
              >
                <Sparkles className="mr-2 h-5 w-5" />
                Generate Complete Book
                <ArrowRight className="ml-2 h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {/* Processing Step */}
        {step === 'processing' && (
          <div className="bg-white rounded-2xl shadow-2xl p-12 text-center">
            <Loader2 className="mx-auto h-20 w-20 text-purple-600 animate-spin mb-6" />
            <h2 className="text-3xl font-semibold mb-3 text-gray-800">
              Creating Your Book
            </h2>
            <p className="text-gray-600 text-lg mb-6">
              {progress}
            </p>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 max-w-md mx-auto">
              <div className="space-y-3 text-left">
                <div className="flex items-center text-sm text-gray-700">
                  <Check className="h-5 w-5 text-green-600 mr-3" />
                  <span>Researching topic with AI agents</span>
                </div>
                <div className="flex items-center text-sm text-gray-700">
                  <Loader2 className="h-5 w-5 text-purple-600 animate-spin mr-3" />
                  <span>Writing {numChapters} chapters in parallel</span>
                </div>
                <div className="flex items-center text-sm text-gray-400">
                  <div className="h-5 w-5 border-2 border-gray-300 rounded-full mr-3" />
                  <span>Formatting and combining chapters</span>
                </div>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-6">
              This may take 3-10 minutes depending on the number of chapters
            </p>
          </div>
        )}

        {/* Results Step */}
        {step === 'results' && result && (
          <div className="space-y-6">
            {/* Success Card */}
            <div className="bg-white rounded-2xl shadow-2xl p-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-3xl font-semibold flex items-center text-gray-800">
                  <Check className="mr-3 text-green-600 h-8 w-8" />
                  Book Generated Successfully!
                </h2>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-xl text-center border border-purple-200">
                  <p className="text-sm text-gray-600 mb-1">Total Chapters</p>
                  <p className="text-4xl font-bold text-purple-600">
                    {result.total_chapters}
                  </p>
                </div>
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-xl text-center border border-blue-200">
                  <p className="text-sm text-gray-600 mb-1">Total Words</p>
                  <p className="text-4xl font-bold text-blue-600">
                    {result.total_words.toLocaleString()}
                  </p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-xl text-center border border-green-200">
                  <p className="text-sm text-gray-600 mb-1">Avg per Chapter</p>
                  <p className="text-4xl font-bold text-green-600">
                    {Math.round(result.total_words / result.total_chapters).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Book Info */}
              <div className="bg-gray-50 rounded-xl p-6 mb-6 border border-gray-200">
                <h3 className="text-2xl font-bold text-gray-800 mb-3">
                  {result.title}
                </h3>
                <div className="space-y-2 text-sm">
                  <p className="text-gray-700">
                    <span className="font-semibold">Topic:</span> {result.topic}
                  </p>
                  <p className="text-gray-700">
                    <span className="font-semibold">Goal:</span> {result.goal}
                  </p>
                </div>
              </div>

              {/* Download Button */}
              <button
                onClick={downloadBook}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-lg hover:from-green-700 hover:to-emerald-700 font-semibold text-lg shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center mb-4"
              >
                <Download className="mr-2 h-5 w-5" />
                Download Book as Markdown
              </button>
            </div>

            {/* Chapters Preview */}
            <div className="bg-white rounded-2xl shadow-2xl p-8">
              <h3 className="text-2xl font-semibold mb-6 text-gray-800">
                Chapters Overview
              </h3>
              <div className="space-y-4">
                {result.chapters.map((chapter) => (
                  <div
                    key={chapter.number}
                    className="border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow bg-gradient-to-r from-white to-gray-50"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center">
                        <span className="bg-purple-600 text-white font-bold px-4 py-2 rounded-lg mr-4 text-lg">
                          {chapter.number}
                        </span>
                        <h4 className="font-semibold text-xl text-gray-800">
                          {chapter.title}
                        </h4>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-500">Words</div>
                        <div className="text-lg font-bold text-purple-600">
                          {chapter.word_count?.toLocaleString()}
                        </div>
                      </div>
                    </div>
                    {chapter.description && (
                      <p className="text-sm text-gray-600 mt-3 pl-16">
                        {chapter.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={resetForm}
                className="flex-1 bg-white border-2 border-gray-300 text-gray-700 py-4 rounded-lg hover:bg-gray-50 font-semibold text-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center"
              >
                <ArrowLeft className="mr-2 h-5 w-5" />
                Create Another Book
              </button>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-6 bg-red-50 border-2 border-red-200 rounded-xl p-6 flex items-start shadow-lg">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-4">
              <h4 className="font-semibold text-red-900 text-lg">Error</h4>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;