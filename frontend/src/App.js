import React, { useState, useCallback } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, XCircle, Loader2, Download, AlertTriangle, Menu, Home, Info, Settings, HelpCircle } from 'lucide-react';


const ShapefileValidationApp = () => {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [validationRun, setValidationRun] = useState(false); // New state
  const [selectedChecks, setSelectedChecks] = useState({
  'OSC Duplicates Check': true,
  'Cluster Overlap Check': true,
  'Cable Granularity Check': true,
  'Non-virtual Closure Validation': true,
  'Point Location Validation': true,
  'Cable Diameter Validation': true,
  'Cable Reference Validation': true,
  'Shapefile Processing': true,
  'GISTOOL_ID Validation': true,
  'Splice Count Report': true
});

// Add this function to handle checkbox changes
const handleCheckboxChange = (checkName) => {
  setSelectedChecks(prev => ({
    ...prev,
    [checkName]: !prev[checkName]
  }));
};

// Add this function to toggle all checkboxes
const toggleAllChecks = (selectAll) => {
  const newState = {};
  Object.keys(selectedChecks).forEach(key => {
    newState[key] = selectAll;
  });
  setSelectedChecks(newState);
};



// Add PDF export function
const handleExportPDF = async () => {
  if (!results) return;

  try {
    const response = await fetch('/api/export-pdf', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        results: results.results,
        filename: results.filename
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'PDF export failed');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `validation_report_${results.filename.replace('.zip', '')}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    setError(`Failed to export PDF: ${err.message}`);
  }
};

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
      setResults(null);
      setValidationRun(false);
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
        setResults(null);
        setValidationRun(false);
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

    // Check file size on client side (500MB limit)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
      setError(`File too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Maximum size is 500MB.`);
      return;
    }

      // Get selected check names
      const checksToRun = Object.entries(selectedChecks)
        .filter(([_, isSelected]) => isSelected)
        .map(([name]) => name);

      if (checksToRun.length === 0) {
        setError("Please select at least one check to run");
        return;
      }

      setLoading(true);
      setError(null);
      setResults(null);

      const formData = new FormData();
      formData.append('file', file);
      formData.append('checks', JSON.stringify(checksToRun));

      try {
        const response = await fetch('/backend/api/validate', {
          method: 'POST',
          body: formData,
        });

      // Check for HTML response (like 413 error pages)
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) {
        if (response.status === 413) {
          throw new Error('File too large. The server cannot process files larger than 500MB. Please try a smaller file.');
        }
        const text = await response.text();
        throw new Error(`Server error: ${text.substring(0, 100)}...`);
      }

      if (!response.ok) {
        if (response.status === 413) {
          throw new Error('File too large. Maximum file size is 500MB.');
        }
        
        // Try to get JSON error message
        try {
          const errorData = await response.json();
          throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        } catch {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
      }

      const data = await response.json();
      //const data = await validateFile(file);
      setResults(data);
      setValidationRun(true);  // Mark validation as run
    } catch (err) {
      console.error('Full error:', err);
      
      // Provide user-friendly error messages
      if (err.message.includes('413') || err.message.includes('Request Entity Too Large')) {
        setError('File too large. Please try a smaller file (maximum 500MB).');
      } else if (err.message.includes('NetworkError') || err.message.includes('Failed to fetch')) {
        setError('Network error. Please check your internet connection and try again.');
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
      //setIsProcessing(false);
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

            {/*Add this component to your UI (after file selection but before Run Validation button)*/}
          <div className="mt-6 bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-medium text-gray-700">Select Checks to Run:</h3>
              <div className="flex space-x-2">
                <button 
                  onClick={() => toggleAllChecks(true)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Select All
                </button>
                <button 
                  onClick={() => toggleAllChecks(false)}
                  className="text-sm text-gray-600 hover:text-gray-800"
                >
                  Deselect All
                </button>
              </div>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(selectedChecks).map(([checkName, isChecked]) => (
                <div key={checkName} className="flex items-center">
                  <input
                    type="checkbox"
                    id={`check-${checkName}`}
                    checked={isChecked}
                    onChange={() => handleCheckboxChange(checkName)}
                    className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500 border-gray-300"
                  />
                  <label 
                    htmlFor={`check-${checkName}`} 
                    className="ml-2 text-sm text-gray-700"
                  >
                    {checkName}
                  </label>
                </div>
              ))}
            </div>
          </div>

            <div className="mt-6 flex flex-col sm:flex-row justify-center items-center gap-4">
              <button
                onClick={handleSubmit}
                disabled={!file || loading}
                className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200"
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

                {validationRun && (
                <button
                  onClick={handleExportPDF}
                  className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-red-600 hover:bg-red-700 transition-colors duration-200"
                >
                  <FileText className="w-5 h-5 mr-2" />
                  Export PDF
              </button>
                )}
            </div>

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


