<script lang='ts'>

    import { emailStore } from '$lib/stores/emailStore';
    import { renderedEmailStore } from '$lib/stores/renderedEmailStore';
    import ArrayEditor from '$lib/components/ArrayEditor.svelte';
    import type { components } from '$lib/types/api';

    type NewsStory = components["schemas"]["NewsStory"];

    // Props
    export let emailType: string;
    export let displayName: string;

    // Get data for this email type from the store
    $: emailData = $emailStore[emailType];
    $: renderedEmail = $renderedEmailStore[emailType] || "";

    // State
    let activeField: string = "";
    let fetchingData: boolean = false;
    let renderingData: boolean = false;
    
    // Add story modal state
    let showAddStoryModal = false;
    let storyUrl = "";
    let selectedStoryField: string | null = null;
    let fetchingStory = false;

    // Get all fields that contain NewsStory arrays
    $: newsStoryFields = emailData ? Object.keys(emailData).filter(
        key => Array.isArray((emailData as any)[key]) && 
               (emailData as any)[key].length > 0 && 
               'headline' in ((emailData as any)[key][0] as any)
    ) : [];

    // Set initial active field when data loads
    $: if (emailData && !activeField) {
        activeField = Object.keys(emailData)[0];
    }

    // Fetch email data from backend
    async function fetchEmailData() {
        fetchingData = true;
        try {
            await emailStore.fetch(emailType);
            if (emailData) {
                activeField = Object.keys(emailData)[0];
            }
        } catch (error) {
            console.error("Error fetching email data:", error);
        } finally {
            fetchingData = false;
        }
    }

    // Pass email data to backend to render html preview
    async function renderEmail() {
        if (!emailData) return;
        
        renderingData = true;
        try {
            await renderedEmailStore.render(emailType, emailData);
        } catch (error) {
            console.error("Error rendering email:", error);
        } finally {
            renderingData = false;
        }
    }

    // Open add story modal
    function openAddStoryModal() {
        showAddStoryModal = true;
        storyUrl = "";
        selectedStoryField = newsStoryFields[0] || null;
    }

    // Close add story modal
    function closeAddStoryModal() {
        showAddStoryModal = false;
        storyUrl = "";
        selectedStoryField = null;
    }

    // Fetch and add story
    async function addStory() {
        if (!storyUrl || !selectedStoryField) return;
        
        fetchingStory = true;
        try {
            const res = await fetch(`http://localhost:8000/news_stories/?url=${encodeURIComponent(storyUrl)}`, {
                method: "POST"
            });
            
            if (!res.ok) {
                const error = await res.json();
                alert(`Error: ${error.detail}`);
                return;
            }
            
            const story: NewsStory = await res.json();
            
            // Add story to the selected field
            if (emailData && Array.isArray((emailData as any)[selectedStoryField])) {
                ((emailData as any)[selectedStoryField] as any[]).push(story);
                emailStore.set(emailType, emailData);
            }
            
            closeAddStoryModal();
        } catch (error) {
            console.error("Error fetching story:", error);
            alert("Failed to fetch story");
        } finally {
            fetchingStory = false;
        }
    }
</script>

<!-- Title -->
<h1>{displayName}</h1>

<!-- Fetch and render buttons -->
<div class="row">
    <div class="mb-3">
        <button 
            class="btn btn-primary" 
            on:click={fetchEmailData}
            disabled={fetchingData}>
            {fetchingData ? 'Fetching...' : 'Fetch Email Data'}
        </button>
        
        {#if emailData}
            <button 
                class="btn btn-info ms-2" 
                on:click={openAddStoryModal}>
                + Add Story by URL
            </button>
        {/if}
    </div>
</div>

<!-- Email not loaded warning -->
{#if !emailData}
    <div class="alert alert-warning" role="alert">
        No email data loaded. Click "Fetch Email Data" to load data from the backend.
    </div>
{:else}

<!-- Two column structure -->
<div class="container-fluid">
    <div class="row">
        <!-- Data Input -->
        <div class="col-md-6">
            <!-- Field navbar -->
            <div class="nav nav-tabs">
                {#each Object.keys(emailData) as field}
                    <button 
                        class="nav-link {field === activeField ? 'active' : ''}" 
                        on:click={() => activeField = field}>
                        {field}
                    </button>
                {/each}
            </div>

            <!-- Field editor -->
            <div class="mt-3">
                <label for="fieldTextarea" class="form-label">{activeField}</label>
                
                {#if typeof (emailData as any)[activeField] === 'string'}
                    <!-- Simple text box if data type is string -->
                    <textarea 
                        id="fieldTextarea"
                        class="form-control" 
                        rows="10"
                        bind:value={(emailData as any)[activeField]}>
                    </textarea>

                {:else if Array.isArray((emailData as any)[activeField])}
                    <!-- Data editor for list of objects -->
                    <ArrayEditor 
                        items={(emailData as any)[activeField]} 
                        itemTemplate={activeField.includes('advert') ? { url: '', image_url: '' } : null} />

                {:else if typeof (emailData as any)[activeField] === 'object' && (emailData as any)[activeField] !== null}
                    <!-- Object editor for single objects with multiple fields -->
                    {#each Object.entries((emailData as any)[activeField]) as [key, value]}
                        <div class="mb-2">
                            <label class="form-label" for="field-{key}">{key}</label>
                            {#if typeof value === 'string' && (value.includes('\n') || value.length > 100)}
                                <textarea 
                                    id="field-{key}"
                                    class="form-control"
                                    rows="4"
                                    bind:value={((emailData as any)[activeField] as any)[key]}>
                                </textarea>
                            {:else}
                                <input 
                                    id="field-{key}"
                                    type="text" 
                                    class="form-control"
                                    bind:value={((emailData as any)[activeField] as any)[key]} />
                            {/if}
                        </div>
                    {/each}
                {/if}
            </div>
        </div>

        <!-- HTML Preview -->
        <div class="col-md-6">
            <div class="mb-2">
                <button 
                    class="btn btn-success btn-sm"
                    on:click={renderEmail}
                    disabled={renderingData || !emailData}>
                    {renderingData ? 'Rendering...' : 'Render Email'}
                </button>
                <button 
                    class="btn btn-secondary btn-sm ms-2"
                    on:click={() => {
                        const blob = new Blob([renderedEmail], { type: 'text/html' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `${emailType}_email_${new Date().toISOString().split('T')[0]}.html`;
                        a.click();
                        URL.revokeObjectURL(url);
                    }}
                    disabled={!emailData}>
                    Download
                </button>
            </div>
            <iframe 
                title="Email Preview" 
                srcdoc={renderedEmail}
                class="border p-3" 
                style="width: 100%; height: 80vh; background-color: #f8f9fa;">
            </iframe>
        </div>
    </div>
</div>

{/if}

<!-- Add Story Modal -->
{#if showAddStoryModal}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-backdrop" on:click={closeAddStoryModal}></div>
    <div class="modal show d-block" tabindex="-1" style="display: flex !important; align-items: center; justify-content: center;">
        <div class="modal-dialog" style="margin: 0; max-width: 500px;">
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div class="modal-content" on:click|stopPropagation>
                <div class="modal-header">
                    <h5 class="modal-title">Add Story by URL</h5>
                    <button type="button" class="btn-close" on:click={closeAddStoryModal} aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label" for="story-url">Story URL</label>
                        <input 
                            type="url" 
                            class="form-control"
                            id="story-url"
                            placeholder="https://www.bailiwickexpress.com/..."
                            bind:value={storyUrl} />
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="story-field">Add to Section</label>
                        <select 
                            class="form-select"
                            id="story-field"
                            bind:value={selectedStoryField}>
                            {#each newsStoryFields as field}
                                <option value={field}>{field}</option>
                            {/each}
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" on:click={closeAddStoryModal}>Cancel</button>
                    <button 
                        type="button" 
                        class="btn btn-primary" 
                        on:click={addStory}
                        disabled={!storyUrl || fetchingStory}>
                        {fetchingStory ? 'Fetching...' : 'Add Story'}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 1040;
    }

    .modal.show {
        z-index: 1050;
    }
</style>
