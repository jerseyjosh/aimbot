<script lang='ts'>
    import { onMount } from 'svelte';

    // State
    let speakers: string[] = [];
    let selectedSpeaker: string = "";
    let script: string = "";
    let isLoadingSpeakers: boolean = false;
    let isFetchingScript: boolean = false;
    let isGenerating: boolean = false;
    let audioUrl: string | null = null;
    let errorMessage: string = "";

    // Fetch available speakers on mount
    onMount(async () => {
        await fetchSpeakers();
    });

    // Fetch list of available speaker voices from backend
    async function fetchSpeakers() {
        isLoadingSpeakers = true;
        errorMessage = "";
        try {
            const res = await fetch('/radio/speakers');
            if (!res.ok) throw new Error('Failed to fetch speakers');
            speakers = await res.json();
            if (speakers.length > 0) {
                selectedSpeaker = speakers[0];
            }
        } catch (error) {
            console.error('Error fetching speakers:', error);
            errorMessage = 'Failed to load speakers. Make sure the backend is running.';
        } finally {
            isLoadingSpeakers = false;
        }
    }

    // Fetch radio news data and generate initial script
    async function fetchScript() {
        if (!selectedSpeaker) {
            errorMessage = 'Please select a speaker first';
            return;
        }

        isFetchingScript = true;
        errorMessage = "";
        try {
            const res = await fetch(`/radio/script?speaker=${encodeURIComponent(selectedSpeaker)}`);
            if (!res.ok) throw new Error('Failed to fetch script');
            const data = await res.json();
            script = data.script;
        } catch (error) {
            console.error('Error fetching script:', error);
            errorMessage = error instanceof Error ? error.message : 'Failed to fetch script';
        } finally {
            isFetchingScript = false;
        }
    }

    // Send script to backend to generate audio
    async function generateAudio() {
        if (!script.trim() || !selectedSpeaker) {
            errorMessage = 'Please enter a script and select a speaker';
            return;
        }

        isGenerating = true;
        errorMessage = "";
        
        // Clear previous audio
        if (audioUrl) {
            URL.revokeObjectURL(audioUrl);
            audioUrl = null;
        }

        try {
            const res = await fetch('/radio/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    speaker_id: selectedSpeaker,
                    script: script,
                    stories: [],
                    weather: ""
                })
            });

            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'Failed to generate audio');
            }

            const audioBlob = await res.blob();
            audioUrl = URL.createObjectURL(audioBlob);
        } catch (error) {
            console.error('Error generating audio:', error);
            errorMessage = error instanceof Error ? error.message : 'Failed to generate audio';
        } finally {
            isGenerating = false;
        }
    }

    // Download generated audio as MP3 file
    function downloadAudio() {
        if (!audioUrl) return;
        
        const a = document.createElement('a');
        a.href = audioUrl;
        a.download = `radio_news_${selectedSpeaker}_${new Date().toISOString().split('T')[0]}.mp3`;
        a.click();
    }
</script>

<!-- Title -->
<div class="container mt-4">

    <h1>Radio News Generator</h1>

    <!-- Error message -->
    {#if errorMessage}
        <div class="alert alert-danger" role="alert">
            {errorMessage}
        </div>
    {/if}

    <!-- Fetch button -->
    <div class="row">
        <div class="mb-3">
            <button 
                class="btn btn-primary" 
                on:click={fetchScript}
                disabled={isFetchingScript || !selectedSpeaker}>
                {isFetchingScript ? 'Fetching...' : 'Fetch Radio Script'}
            </button>
        </div>
    </div>

    <!-- Two column structure -->
    <div class="row mt-4">
        <!-- Script Editor -->
        <div class="col-md-6">
            <!-- Speaker selection -->
            <div class="mb-3">
                <label for="speaker-select" class="form-label">Speaker Voice</label>
                <select 
                    id="speaker-select"
                    class="form-select" 
                    bind:value={selectedSpeaker}
                    disabled={isLoadingSpeakers || speakers.length === 0}>
                    {#if isLoadingSpeakers}
                        <option>Loading speakers...</option>
                    {:else if speakers.length === 0}
                        <option>No speakers available</option>
                    {:else}
                        {#each speakers as speaker}
                            <option value={speaker}>{speaker}</option>
                        {/each}
                    {/if}
                </select>
            </div>

            <!-- Script editor -->
            <div class="mb-3">
                <label for="script-textarea" class="form-label">Radio Script</label>
                <textarea 
                    id="script-textarea"
                    class="form-control" 
                    rows="20"
                    placeholder="Enter your radio news script here..."
                    bind:value={script}>
                </textarea>
            </div>

            <!-- Generate button -->
            <div class="mb-3">
                <button 
                    class="btn btn-primary" 
                    on:click={generateAudio}
                    disabled={isGenerating || !script.trim() || !selectedSpeaker}>
                    {isGenerating ? 'Generating...' : 'Generate Audio'}
                </button>
            </div>
        </div>

        <!-- Audio Player -->
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Audio Output</h5>
                    
                    {#if audioUrl}
                        <div class="mb-3">
                            <audio controls class="w-100">
                                <source src={audioUrl} type="audio/mpeg">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                        
                        <button 
                            class="btn btn-success btn-sm" 
                            on:click={downloadAudio}>
                            Download Audio
                        </button>
                    {:else}
                        <p class="text-muted">
                            No audio generated yet. Enter a script and click "Generate Audio" to create your radio news.
                        </p>
                    {/if}
                </div>
            </div>

            <div class="card mt-3">
                <div class="card-body">
                    <h6 class="card-subtitle mb-2 text-muted">Tips</h6>
                    <ul class="small">
                        <li>The speaker may need to be changed manually before generating.</li>
                        <li>Phrases like <b>£1.2 million</b> should be changed to <b>1 point 2 million pounds</b> to ensure proper pronunciation.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>