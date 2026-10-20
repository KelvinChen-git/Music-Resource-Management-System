<script setup>
defineProps({name: {type: String, required: true}})
</script>
<template><svg class="icon" aria-hidden="true"><use :href="'#i-'+name" /></svg></template>
