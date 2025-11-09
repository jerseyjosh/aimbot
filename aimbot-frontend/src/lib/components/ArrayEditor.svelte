<script lang="ts">

    // Props
    export let items: any[];
    export let itemTemplate: any = null; // Optional template for empty arrays

    // Extract column names from the first item's keys, or from template
    $: columns = items.length > 0 
        ? Object.keys(items[0]) 
        : (itemTemplate ? Object.keys(itemTemplate) : []);

    // Drag and drop state
    let draggedIndex: number | null = null;

    // Modal state
    let showModal = false;
    let editingIndex: number | null = null;
    let editingItem: any = null;
    let isAddingNew = false; // Track if we're adding a new item

    // When dragging starts, store which row we're dragging
    function handleDragStart(index: number) {
        draggedIndex = index;
    }

    // When dropping on a row, reorder the array
    function handleDrop(targetIndex: number) {
        if (draggedIndex === null) return;
        
        // Remove item from old position
        const [draggedItem] = items.splice(draggedIndex, 1);
        // Insert at new position
        items.splice(targetIndex, 0, draggedItem);
        
        // Trigger reactivity by reassigning
        items = items;
        draggedIndex = null;
    }

    // Allow drop by preventing default
    function handleDragOver(event: DragEvent) {
        event.preventDefault();
    }

    // Open modal to edit an item
    function openEditModal(index: number) {
        editingIndex = index;
        // Create a copy so we can cancel changes
        editingItem = { ...items[index] };
        showModal = true;
    }

    // Save changes from modal
    function saveChanges() {
        if (editingIndex !== null && editingItem !== null) {
            if (isAddingNew) {
                // Add the new item to the array
                items.push(editingItem);
            } else {
                // Update existing item
                items[editingIndex] = editingItem;
            }
            items = items; // Trigger reactivity
        }
        closeModal();
    }

    // Close modal without saving
    function closeModal() {
        showModal = false;
        editingIndex = null;
        editingItem = null;
        isAddingNew = false;
    }

    // Delete a row
    function deleteRow(index: number) {
        if (confirm('Are you sure you want to delete this item?')) {
            items.splice(index, 1);
            items = items; // Trigger reactivity
        }
    }

    // Add a new row
    function addNewRow() {
        // Create a new empty item with the same structure as existing items or template
        const newItem: any = {};
        const template = itemTemplate || (items.length > 0 ? items[0] : {});
        
        Object.keys(template).forEach(column => {
            newItem[column] = ''; // Initialize all fields as empty strings
        });
        
        // Don't add to array yet - just open modal
        editingItem = newItem;
        editingIndex = items.length; // Would be the index if added
        isAddingNew = true;
        showModal = true;
    }

</script>

<!-- Dataframe -->
<div class="mb-2">
    <button class="btn btn-sm btn-success" on:click={addNewRow} disabled={columns.length === 0}>
        + Add New Item
    </button>
</div>

{#if items.length > 0}
<div class="table-responsive">
    <table class="table table-bordered table-sm">

        <!-- Header row with column names -->
        <thead>
            <tr>
                <th style="width: 40px;">🗑️</th>  <!-- Delete button column -->
                <th style="width: 40px;">#</th>  <!-- Row number column -->
                {#each columns as column}
                    <th>{column}</th>
                {/each}
            </tr>
        </thead>

        <!-- Data rows -->
        <tbody>
            <!-- Loop through each item in the array -->
            {#each items as item, index}
                <tr 
                    draggable="true"
                    on:dragstart={() => handleDragStart(index)}
                    on:drop|preventDefault={() => handleDrop(index)}
                    on:dragover={handleDragOver}
                    on:click={() => openEditModal(index)}
                    class:dragging={draggedIndex === index}
                    style="cursor: move;">
                    <td on:click|stopPropagation>
                        <button 
                            class="btn btn-sm btn-danger"
                            on:click={() => deleteRow(index)}>
                            ✕
                        </button>
                    </td>
                    <td>{index + 1}</td>  <!-- Display row number (1-indexed) -->
                    <!-- Loop through each column for this row - display only -->
                    {#each columns as column}
                        <td class="text-truncate" style="max-width: 150px;">
                            {item[column]}
                        </td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
</div>
{:else}
<div class="alert alert-info">
    No items yet. Click "Add New Item" to create one.
</div>
{/if}

<!-- Modal for editing -->
{#if showModal && editingItem}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-backdrop" on:click={closeModal}></div>
    <div class="modal show d-block" tabindex="-1">
        <div class="modal-dialog">
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div class="modal-content" on:click|stopPropagation>
                <div class="modal-header">
                    <h5 class="modal-title">Edit Item {editingIndex !== null ? editingIndex + 1 : ''}</h5>
                    <button type="button" class="btn-close" on:click={closeModal} aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    {#each columns as column}
                        <div class="mb-3">
                            <label class="form-label" for="edit-{column}">{column}</label>
                            <input 
                                type="text" 
                                class="form-control"
                                id="edit-{column}"
                                bind:value={editingItem[column]} />
                        </div>
                    {/each}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" on:click={closeModal}>Cancel</button>
                    <button type="button" class="btn btn-primary" on:click={saveChanges}>Save Changes</button>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    /* Visual feedback for the row being dragged */
    .dragging {
        opacity: 0.5;
    }
    
    /* Hover effect when dragging over a row */
    tr[draggable="true"]:hover {
        background-color: #f0f0f0;
    }

    /* Modal backdrop */
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 1040;
    }

    /* Modal positioning */
    .modal.show {
        z-index: 1050;
        display: flex !important;
        align-items: center;
        justify-content: center;
    }

    /* Center and size the modal dialog */
    :global(.modal-dialog) {
        margin: 0;
        max-width: 500px;
        width: 90%;
    }

    /* Constrain modal body height */
    :global(.modal-body) {
        max-height: 60vh;
        overflow-y: auto;
    }
</style>
