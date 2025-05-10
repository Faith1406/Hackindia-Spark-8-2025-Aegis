// Global state variables
let isRecording = false;
let sessionId = null;
let pollingInterval = null;
let lastChunkId = null;
let currentlyPlayingButton = null;
let audioPlayer;
let startBtn;
let stopBtn;
let downloadBtn;
let statusDot;
let statusText;
let chunksContainer;
let micThresholdSlider;
let speakerThresholdSlider;
let micThresholdValue;
let speakerThresholdValue;
let transcriptFilePath = "transcriptions/transcription.txt";  // Fixed path

// Store speaker colors for consistent UI
const speakerColors = {};
const colorPalette = [
    '#4CAF50',  // Green (reserved for "You")
    '#00bfff',  // Electric Blue
    '#ff5722',  // Deep Orange
    '#9c27b0',  // Purple
    '#ff9800',  // Orange
    '#2196f3',  // Blue
    '#f44336',  // Red
    '#673ab7',  // Deep Purple
    '#009688',  // Teal
    '#cddc39',  // Lime
];

document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM element references
    startBtn = document.getElementById('startBtn');
    stopBtn = document.getElementById('stopBtn');
    downloadBtn = document.getElementById('downloadBtn');
    statusDot = document.getElementById('statusDot');
    statusText = document.getElementById('statusText');
    chunksContainer = document.getElementById('chunks-container');
    audioPlayer = document.getElementById('audioPlayer');
    micThresholdSlider = document.getElementById('micThreshold');
    speakerThresholdSlider = document.getElementById('speakerThreshold');
    micThresholdValue = document.getElementById('micThresholdValue');
    speakerThresholdValue = document.getElementById('speakerThresholdValue');
    
    // Event listeners
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    downloadBtn.addEventListener('click', downloadTranscript);
    
    // Threshold sliders
    micThresholdSlider.addEventListener('input', updateMicThreshold);
    speakerThresholdSlider.addEventListener('input', updateSpeakerThreshold);
    
    // Check initial status
    checkStatus();
});

// Assign a consistent color to each speaker
const getSpeakerColor = (speakerId) => {
    // "You" (mic source) always gets the first color
    if (speakerId === 'You') {
        return colorPalette[0];
    }
    
    // If this speaker already has a color, return it
    if (speakerColors[speakerId]) {
        return speakerColors[speakerId];
    }
    
    // Assign a new color from the palette
    const colorIndex = (Object.keys(speakerColors).length % (colorPalette.length - 1)) + 1;
    speakerColors[speakerId] = colorPalette[colorIndex];
    return speakerColors[speakerId];
};

// Functions for UI state
const updateUIState = (recording) => {
    isRecording = recording;
    
    // Update buttons
    startBtn.disabled = recording;
    stopBtn.disabled = !recording;
    downloadBtn.disabled = recording;
    
    // Update status indicator
    if (recording) {
        statusDot.classList.add('active');
        statusText.classList.add('active');
        statusText.textContent = 'Recording...';
    } else {
        statusDot.classList.remove('active');
        statusText.classList.remove('active');
        statusText.textContent = 'Inactive';
    }
};

const startRecording = async () => {
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessionId = data.session_id;
            updateUIState(true);
            startPolling();
            
            // Reset speaker colors for new session
            Object.keys(speakerColors).forEach(key => {
                if (key !== 'You') {
                    delete speakerColors[key];
                }
            });
            
            // Clear previous conversation
            chunksContainer.innerHTML = '';
        }
    } catch (error) {
        console.error('Error starting recording:', error);
    }
};

const stopRecording = async () => {
    try {
        const response = await fetch('/api/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateUIState(false);
            stopPolling();
            
            // Enable download button for fixed transcript file
            downloadBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error stopping recording:', error);
    }
};

const downloadTranscript = () => {
    // Use the fixed transcript path
    const transcriptPath = "transcriptions/transcription.txt";
    
    // Create a temporary link to download the file
    const a = document.createElement('a');
    a.href = `/download/${transcriptPath}`;
    a.download = 'transcription.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};

// Functions for threshold control
const updateMicThreshold = async () => {
    const threshold = micThresholdSlider.value;
    micThresholdValue.textContent = threshold;
    
    try {
        // Only send to server if we're already recording
        if (isRecording) {
            const response = await fetch('/api/set_mic_threshold', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ threshold: threshold })
            });
            
            const data = await response.json();
            if (!data.success) {
                console.error('Error updating mic threshold');
            }
        }
    } catch (error) {
        console.error('Error updating mic threshold:', error);
    }
};

const updateSpeakerThreshold = async () => {
    const threshold = speakerThresholdSlider.value;
    speakerThresholdValue.textContent = threshold;
    
    try {
        // Only send to server if we're already recording
        if (isRecording) {
            const response = await fetch('/api/set_speaker_threshold', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ threshold: threshold })
            });
            
            const data = await response.json();
            if (!data.success) {
                console.error('Error updating speaker threshold');
            }
        }
    } catch (error) {
        console.error('Error updating speaker threshold:', error);
    }
};

// Functions for fetching and displaying chunks
const fetchChunks = async () => {
    try {
        const queryParams = lastChunkId ? `?last_chunk_id=${lastChunkId}` : '';
        const response = await fetch(`/api/chunks${queryParams}`);
        const data = await response.json();
        
        if (data.chunks && data.chunks.length > 0) {
            appendChunks(data.chunks);
            // Update last chunk ID for next poll
            lastChunkId = data.chunks[data.chunks.length - 1].chunk_id;
        }
    } catch (error) {
        console.error('Error fetching chunks:', error);
    }
};

const appendChunks = (chunks) => {
    chunks.forEach(chunk => {
        const chunkElement = document.createElement('div');
        chunkElement.className = `transcription-chunk ${chunk.source || 'unknown'}`;
        chunkElement.dataset.chunkId = chunk.chunk_id;
        
        // Determine speaker display name and color
        let speakerName;
        let speakerColor;
        
        if (chunk.source === 'mic') {
            speakerName = 'You';
            speakerColor = getSpeakerColor('You');
        } else if (chunk.speaker_id) {
            speakerName = chunk.speaker_id;
            speakerColor = getSpeakerColor(chunk.speaker_id);
        } else {
            speakerName = 'Speaker';
            speakerColor = getSpeakerColor('Unknown Speaker');
        }
        
        // Set border color based on speaker
        chunkElement.style.borderLeftColor = speakerColor;
        
        // Create play button
        const playButton = document.createElement('button');
        playButton.className = 'play-button';
        playButton.innerHTML = '<i class="fas fa-play"></i>';
        playButton.dataset.audioPath = `/api/audio/${chunk.chunk_id}`;
        
        // Create content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'chunk-content';
        
        // Create timestamp element
        const timestampElement = document.createElement('div');
        timestampElement.className = 'chunk-timestamp';
        timestampElement.textContent = chunk.timestamp;
        
        // Create source badge with speaker name
        const sourceBadge = document.createElement('span');
        sourceBadge.className = `source-badge ${chunk.source || 'unknown'}`;
        sourceBadge.textContent = speakerName;
        sourceBadge.style.backgroundColor = speakerColor;
        
        // Create text element
        const textElement = document.createElement('div');
        textElement.className = 'chunk-text';
        textElement.textContent = chunk.text;
        
        // Add play button event listener
        playButton.addEventListener('click', function() {
            playAudio(this);
        });
        
        // Assemble the chunk
        contentDiv.appendChild(timestampElement);
        contentDiv.appendChild(sourceBadge);
        contentDiv.appendChild(textElement);
        
        chunkElement.appendChild(playButton);
        chunkElement.appendChild(contentDiv);
        
        chunksContainer.appendChild(chunkElement);
    });
    
    // Update the legend with all speakers
    updateSpeakerLegend();
    
    // Scroll to bottom
    chunksContainer.scrollTop = chunksContainer.scrollHeight;
};

// Update the legend with all speaker colors
const updateSpeakerLegend = () => {
    const legendElement = document.querySelector('.legend');
    if (!legendElement) return;
    
    // Clear existing legend
    legendElement.innerHTML = '';
    
    // Add each speaker to the legend
    Object.keys(speakerColors).forEach(speakerId => {
        const color = speakerColors[speakerId];
        
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        
        const badge = document.createElement('span');
        badge.className = 'source-badge';
        badge.textContent = speakerId;
        badge.style.backgroundColor = color;
        
        legendItem.appendChild(badge);
        legendItem.appendChild(document.createTextNode(
            speakerId === 'You' ? ' Your microphone' : ' Computer audio'
        ));
        
        legendElement.appendChild(legendItem);
    });
};

const playAudio = (button) => {
    const audioPath = button.dataset.audioPath;
    
    // If we're already playing this audio, pause it
    if (button === currentlyPlayingButton && !audioPlayer.paused) {
        audioPlayer.pause();
        button.innerHTML = '<i class="fas fa-play"></i>';
        button.classList.remove('playing');
        currentlyPlayingButton = null;
        return;
    }
    
    // Reset any previous playing button
    if (currentlyPlayingButton) {
        currentlyPlayingButton.innerHTML = '<i class="fas fa-play"></i>';
        currentlyPlayingButton.classList.remove('playing');
    }
    
    // Set current button
    currentlyPlayingButton = button;
    button.innerHTML = '<i class="fas fa-pause"></i>';
    button.classList.add('playing');
    
    // Play the audio
    audioPlayer.src = audioPath;
    audioPlayer.play().catch(error => {
        console.error('Error playing audio:', error);
        button.innerHTML = '<i class="fas fa-play"></i>';
        button.classList.remove('playing');
        currentlyPlayingButton = null;
    });
    
    // When audio ends, reset the button
    audioPlayer.onended = () => {
        button.innerHTML = '<i class="fas fa-play"></i>';
        button.classList.remove('playing');
        currentlyPlayingButton = null;
    };
};

// Functions for polling and status
const startPolling = () => {
    // Clear any existing interval
    stopPolling();
    
    // Start polling for new chunks every second
    pollingInterval = setInterval(fetchChunks, 1000);
};

const stopPolling = () => {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
};

const checkStatus = async () => {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.active) {
            sessionId = data.session_id;
            updateUIState(true);
            startPolling();
        } else {
            updateUIState(false);
            // Since we have a fixed transcript file, the download button should be enabled by default
            downloadBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
};