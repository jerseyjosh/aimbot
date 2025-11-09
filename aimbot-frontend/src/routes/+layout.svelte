<script lang="ts">
	import { onMount } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import 'bootstrap/dist/css/bootstrap.min.css';
	let { children } = $props();
	onMount(() => {
		// Bootstrap JS (for dropdowns, etc.)
		import('bootstrap');
	});

</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<nav class="navbar navbar-expand-lg navbar-light bg-light">
	<div class="container-fluid">
		<a class="navbar-brand" href="/">aimbot</a>
		<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
			<span class="navbar-toggler-icon"></span>
		</button>
		<div class="collapse navbar-collapse" id="navbarNav">
			<ul class="navbar-nav">
				<li class="nav-item dropdown">
					<button class="nav-link dropdown-toggle btn btn-link" id="emailsDropdown" type="button" data-bs-toggle="dropdown" aria-expanded="false">
						emails
					</button>
					<ul class="dropdown-menu" aria-labelledby="emailsDropdown">
						<li><a class="dropdown-item" href="/be_email">BE Email</a></li>
						<li><a class="dropdown-item" href="/ge_email">GE Email</a></li>
						<li><a class="dropdown-item" href="/jep_email">JEP Email</a></li>
						<li><a class="dropdown-item" href="/aim_premium">AIM Premium Email</a></li>
					</ul>
				</li>
			</ul>
		</div>
	</div>
</nav>

{@render children()}
