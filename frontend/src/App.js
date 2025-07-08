import React, { useState, useCallback } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, XCircle, Loader2, Download, AlertTriangle, Menu, Home, Info, Settings, HelpCircle } from 'lucide-react';

const ShapefileValidationApp = () => {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile && droppedFile.name.endsWith('.zip')) {
      setFile(droppedFile);
      setError(null);
    } else {
      setError("Please upload a ZIP file");
    }
  }, []);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.zip')) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError("File must be a ZIP archive");
      }
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      setError("Please select a file");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null); // Explicitly reset results

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Use different base URLs for development vs production
      const baseUrl = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:5000' 
        : '';
      
      const response = await fetch(`${baseUrl}/validate`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - let browser set it with boundary
      });

      // Check for HTML response
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) {
        const text = await response.text();
        throw new Error(`Server returned HTML: ${text.substring(0, 100)}...`);
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Full error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getResultIcon = (status) => {
    if (status === null) return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    if (status === true) return <XCircle className="w-5 h-5 text-red-500" />;
    return <CheckCircle className="w-5 h-5 text-green-500" />;
  };

  const getResultColor = (status) => {
    if (status === null) return 'border-yellow-200 bg-yellow-50';
    if (status === true) return 'border-red-200 bg-red-50';
    return 'border-green-200 bg-green-50';
  };

  const formatMessage = (message) => {
    return message.split('\n').map((line, index) => {
      if (line.includes('⛔')) {
        return <div key={index} className="text-red-600 font-medium">{line}</div>;
      } else if (line.includes('⚠️')) {
        return <div key={index} className="text-yellow-600 font-medium">{line}</div>;
      } else if (line.includes('✅')) {
        return <div key={index} className="text-green-600 font-medium">{line}</div>;
      } else if (line.includes('❌')) {
        return <div key={index} className="text-red-600">{line}</div>;
      } else if (line.includes('🔍')) {
        return <div key={index} className="text-blue-600 font-medium">{line}</div>;
      } else if (line.startsWith('---')) {
        return <hr key={index} className="my-2 border-gray-300" />;
      } else {
        return <div key={index} className="text-gray-700">{line}</div>;
      }
    });
  };

  return (
    <div className="min-h-screen  to-indigo-100">
      {/* Header */}
      <header className="bg-amber-400 shadow-lg">
        <div className="max-w-8xl mx-auto px-5">
          <div className="flex justify-between items-center py-4">
            {/* Logo */}
            <div className="flex items-center space-x-2">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center">
                <img 
                  src="/logo.png" 
                  alt="M.Design Logo" 
                />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">M.Design</h1>
                <p className="text-sm text-gray-600">Comsof Validation Suite</p>
              </div>
            </div>

            {/* Desktop Menu */}
            <nav className="hidden md:flex space-x-8">
              <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                <Home className="w-4 h-4" />
                <span>Home</span>
              </a>
              <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                <Info className="w-4 h-4" />
                <span>About</span>
              </a>
              <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                <HelpCircle className="w-4 h-4" />
                <span>Help</span>
              </a>
              <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                <Settings className="w-4 h-4" />
                <span>Settings</span>
              </a>
            </nav>

            {/* Mobile Menu Button */}
            <button
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <Menu className="w-6 h-6 text-gray-700" />
            </button>
          </div>

          {/* Mobile Menu */}
          {menuOpen && (
            <div className="md:hidden py-4 border-t border-gray-200">
              <nav className="flex flex-col space-y-4">
                <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                  <Home className="w-4 h-4" />
                  <span>Home</span>
                </a>
                <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                  <Info className="w-4 h-4" />
                  <span>About</span>
                </a>
                <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                  <HelpCircle className="w-4 h-4" />
                  <span>Help</span>
                </a>
                <a href="#" className="flex items-center space-x-2 text-gray-700 hover:text-blue-600 transition-colors">
                  <Settings className="w-4 h-4" />
                  <span>Settings</span>
                </a>
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto p-4">
        {/* Title Section */}
        <div className="text-center mb-8 mt-8">
          <p className="text-gray-600 text-lg">
            Upload your ZIP file to validate Comsof output shapefiles
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <div className="text-center">
            <div
              className={`border-2 border-dashed rounded-lg p-8 transition-all duration-200 ${
                dragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-700 mb-2">
                Drop your ZIP file here or click to browse
              </h3>
              <p className="text-gray-500 mb-4">
                Supports ZIP files containing Comsof output shapefiles
              </p>
              
              <input
                type="file"
                accept=".zip"
                onChange={handleFileChange}
                className="hidden"
                id="file-input"
              />
              <label
                htmlFor="file-input"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 cursor-pointer transition-colors duration-200"
              >
                <FileText className="w-5 h-5 mr-2" />
                Choose File
              </label>
            </div>

            {file && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-center">
                  <FileText className="w-5 h-5 text-blue-500 mr-2" />
                  <span className="text-gray-700 font-medium">{file.name}</span>
                  <span className="text-gray-500 ml-2">
                    ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
              </div>
            )}

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-red-700">{error}</span>
                </div>
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!file || loading}
              className="mt-6 inline-flex items-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Validating...
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5 mr-2" />
                  Run Validation
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Section - Summary First, then Details */}
        {results && results.results && (
          <>
            {/* Validation Summary */}
            <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
              <div className="flex items-center mb-6">
                <CheckCircle className="w-6 h-6 text-green-500 mr-2" />
                <h2 className="text-2xl font-bold text-gray-800">
                  Validation Summary for {results.filename}
                </h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-6 bg-green-50 rounded-lg border border-green-200">
                  <div className="text-3xl font-bold text-green-600 mb-2">
                    {results.results.filter(([,status]) => status === false).length}
                  </div>
                  <div className="text-green-800 font-medium">Tests Passed</div>
                  <CheckCircle className="w-8 h-8 text-green-500 mx-auto mt-2" />
                </div>
                
                <div className="text-center p-6 bg-red-50 rounded-lg border border-red-200">
                  <div className="text-3xl font-bold text-red-600 mb-2">
                    {results.results.filter(([,status]) => status === true).length}
                  </div>
                  <div className="text-red-800 font-medium">Tests Failed</div>
                  <XCircle className="w-8 h-8 text-red-500 mx-auto mt-2" />
                </div>
                
                <div className="text-center p-6 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="text-3xl font-bold text-yellow-600 mb-2">
                    {results.results.filter(([,status]) => status === null).length}
                  </div>
                  <div className="text-yellow-800 font-medium">Errors</div>
                  <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mt-2" />
                </div>
              </div>
            </div>

            {/* Detailed Results */}
            <div className="bg-white rounded-xl shadow-lg p-8">
              <div className="flex items-center mb-6">
                <FileText className="w-6 h-6 text-blue-500 mr-2" />
                <h2 className="text-2xl font-bold text-gray-800">
                  Detailed Validation Results
                </h2>
              </div>

              <div className="grid gap-6">
                {results.results.map(([name, status, message], index) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-6 ${getResultColor(status)}`}
                  >
                    <div className="flex items-center mb-4">
                      {getResultIcon(status)}
                      <h3 className="text-lg font-semibold text-gray-800 ml-2">
                        {name}
                      </h3>
                    </div>
                    
                    <div className="font-mono text-sm bg-white rounded-lg p-4 border">
                      {typeof message === 'string' ? formatMessage(message) : JSON.stringify(message)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ShapefileValidationApp;