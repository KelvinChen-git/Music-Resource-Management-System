<template>
  <div class="recyclebin-settings-container">
    <div class="settings-header">
      <h1>Recycle Bin Settings</h1>
      <p class="description">Configure retention period and automatic cleanup rules for the recycle bin.</p>
    </div>

    <el-card class="settings-card" v-loading="loading">
      <el-form :model="settings" label-width="180px" :rules="rules" ref="settingsForm">
        <h3>Retention & Cleanup</h3>

        <el-form-item label="Default Retention (days)" prop="defaultRetentionDays">
          <el-input-number
            v-model="settings.defaultRetentionDays"
            :min="1"
            :max="365"
          />
          <span class="setting-tip">Number of days items are kept before permanent deletion.</span>
        </el-form-item>

        <el-form-item label="Enable Auto Cleanup" prop="autoCleanupEnabled">
          <el-switch v-model="settings.autoCleanupEnabled" />
          <span class="setting-tip">Automatically delete items permanently after the retention period expires.</span>
        </el-form-item>

        <el-form-item label="Auto Cleanup Time" prop="autoCleanupTime">
          <el-time-picker
            v-model="settings.autoCleanupTime"
            placeholder="Select time"
            format="HH:mm:ss"
            value-format="HH:mm:ss"  
            :disabled="!settings.autoCleanupEnabled"
          />
          <span class="setting-tip">Time of day when the automatic cleanup process runs.</span>
        </el-form-item>

        <el-divider />

        <el-form-item>
          <el-button type="primary" @click="saveSettings" :loading="saving">Save Settings</el-button>
          <el-button @click="resetSettings">Reset</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRecycleBinSettings, updateRecycleBinSettings } from '@/api/recycleBinSettings' // Import API functions

// Form reference
const settingsForm = ref(null)

// Loading states
const loading = ref(false)
const saving = ref(false)

// Settings form data - aligned with backend model
const settings = reactive({
  id: null, // Store the ID if needed for updates
  defaultRetentionDays: 30,
  autoCleanupEnabled: true,
  autoCleanupTime: '03:00:00', // Expect HH:mm:ss format
})

// Form validation rules
const rules = {
  defaultRetentionDays: [
    { required: true, message: 'Please set the retention period', trigger: 'blur' },
    { type: 'number', min: 1, max: 365, message: 'Retention period must be between 1 and 365 days', trigger: 'blur' }
  ],
  autoCleanupTime: [
     // Only required if auto cleanup is enabled
     { validator: (rule, value, callback) => {
         if (settings.autoCleanupEnabled && !value) {
           callback(new Error('Please select auto cleanup time'));
         } else {
           callback();
         }
       }, trigger: 'change' 
    }
  ]
}

// Load current settings from backend
const loadSettings = async () => {
  loading.value = true
  try {
    const res = await getRecycleBinSettings()
    if (res.data) {
        // Assign fetched data to the reactive object
        Object.assign(settings, res.data)
        // Ensure boolean value for switch
        settings.autoCleanupEnabled = Boolean(settings.autoCleanupEnabled)
    } else {
         ElMessage.warning('Could not load settings, using defaults.');
    }
  } catch (error) {
    ElMessage.error('Failed to load settings: ' + error.message)
  } finally {
    loading.value = false
  }
}

// Save settings to backend
const saveSettings = async () => {
  try {
    await settingsForm.value.validate()

    saving.value = true
    
    // Prepare data for the API call
    const settingsData = {
        id: settings.id, // Include ID if it exists
        defaultRetentionDays: settings.defaultRetentionDays,
        autoCleanupEnabled: settings.autoCleanupEnabled,
        autoCleanupTime: settings.autoCleanupTime
    }

    await updateRecycleBinSettings(settingsData)

    ElMessage.success('Settings saved successfully')
  } catch (error) {
    if (error && error instanceof Array) { // Handle validation errors
        console.log('Validation failed');
    } else {
        ElMessage.error('Save failed: ' + (error?.message || 'Unknown error'))
    }
  } finally {
    saving.value = false
  }
}

// Reset settings by reloading from backend
const resetSettings = () => {
  ElMessageBox.confirm(
    'Are you sure you want to reset the form? Unsaved changes will be lost.',
    'Reset Confirmation',
    {
      confirmButtonText: 'Confirm',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  )
    .then(() => {
      loadSettings() // Reload settings from backend
      ElMessage.info('Settings form has been reset to the last saved state.')
    })
    .catch(() => { /* User cancelled */ })
}

// Load settings when the component mounts
onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.recyclebin-settings-container {
  padding: 20px;
  max-width: 700px; /* Adjusted max-width */
  margin: 0 auto;
}

.settings-header {
  margin-bottom: 24px;
}

.settings-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.description {
  color: #606266;
  font-size: 14px;
}

.settings-card {
  margin-bottom: 20px;
}

.settings-card h3 {
  font-size: 16px;
  margin: 5px 0 20px 0; /* Increased bottom margin */
  padding-bottom: 10px;
  border-bottom: 1px solid #EBEEF5;
}

.setting-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 13px;
  display: block; /* Make tip appear on new line */
  margin-top: 5px; /* Add space above tip */
}

:deep(.el-form-item) {
  margin-bottom: 25px;
}

:deep(.el-input-number) {
  width: 150px;
}

/* Remove slider styles as it's no longer used */
/* :deep(.el-slider) {
  width: 300px;
} */
</style>