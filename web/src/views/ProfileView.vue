<script setup>
import { ref, onMounted, computed, reactive, onBeforeUnmount } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox, ElUpload, ElForm, ElFormItem, ElInput, ElButton, ElAvatar } from 'element-plus'
import { RefreshRight, UploadFilled, Edit, Check, Close } from '@element-plus/icons-vue'
import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'
import { exportAllData, deleteAccount, updateProfile, uploadAvatar } from '@/api/auth'
import { exportMusicFiles } from '@/api/user'
import { useRouter } from 'vue-router'
import { getAvatarUrl } from '@/utils/url'

const userStore = useUserStore()
const router = useRouter()
const loading = ref(false)
const changePasswordDialogVisible = ref(false)
const exportLoading = ref(false)
const deleteLoading = ref(false)
const exportMusicLoading = ref(false)

// Editing state
const isEditing = ref(false)
const editableUserInfo = ref({})
const selectedAvatarFile = ref(null)
const avatarPreviewUrl = ref(null)
const saveLoading = ref(false)

// User information
const userInfo = computed(() => userStore.userInfo)

// Computed property for the avatar source URL
const avatarSrc = computed(() => {
  if (isEditing.value) {
    // In edit mode:
    // Priority 1: Local preview URL for newly selected file
    if (avatarPreviewUrl.value) {
      return avatarPreviewUrl.value;
    }
    // Priority 2: URL constructed from the *editable* avatar path
    if (editableUserInfo.value?.avatar) {
      return getAvatarUrl(editableUserInfo.value.avatar);
    }
  } else {
    // In view mode:
    // Use the URL constructed from the authoritative user info in the store
    if (userStore.userInfo?.avatar) {
       return getAvatarUrl(userStore.userInfo.avatar);
    }
  }
  // Fallback: return null so the default slot (initials) is used
  return null;
});

// Load user information
const loadUserInfo = async () => {
  loading.value = true
  try {
    await userStore.getUserInfo()
  } catch (error) {
    console.error('Failed to load profile information:', error)
    ElMessage.error('')
  } finally {
    loading.value = false
  }
}

// Get default avatar
const getDefaultAvatar = () => {
  return userInfo.value.name ? userInfo.value.name.charAt(0).toUpperCase() : 'U'
}

// Load user information when component mounts
onMounted(() => {
  loadUserInfo().then(() => {
    // Initialize editableUserInfo after loading
    resetEditableInfo()
  })
})

// Cleanup preview URL before unmount
onBeforeUnmount(() => {
  if (avatarPreviewUrl.value) {
    URL.revokeObjectURL(avatarPreviewUrl.value)
  }
})

// Function to reset editable info from store
const resetEditableInfo = () => {
  // Deep copy to prevent modifying the store directly
  editableUserInfo.value = JSON.parse(JSON.stringify(userStore.userInfo))
}

// Function to enter edit mode
const enterEditMode = () => {
  resetEditableInfo()
  isEditing.value = true
}

// Handle avatar selection change
const handleAvatarChange = (uploadFile) => {
  if (avatarPreviewUrl.value) {
    URL.revokeObjectURL(avatarPreviewUrl.value) // Revoke previous preview
  }

  const file = uploadFile.raw
  if (!file) return

  // Basic validation (optional but recommended)
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('Please upload an image file (e.g., JPG, PNG, GIF)!')
    return
  }
  if (!isLt2M) {
    ElMessage.error('Avatar image size cannot exceed 2MB!')
    return
  }

  selectedAvatarFile.value = file
  avatarPreviewUrl.value = URL.createObjectURL(file)
}

// Handle saving the profile changes
const handleSaveProfile = async () => {
  saveLoading.value = true
  let avatarPath = editableUserInfo.value.avatar // Keep old path initially

  try {
    // 1. Upload new avatar if selected
    if (selectedAvatarFile.value) {
      try {
        console.log("Uploading avatar...");
        const uploadResponse = await uploadAvatar(selectedAvatarFile.value)
        // Check if upload was successful and filePath exists
        if (uploadResponse && uploadResponse.data && uploadResponse.data.filePath) {
          avatarPath = uploadResponse.data.filePath // Use the new path returned by backend
           console.log("Avatar uploaded successfully, path:", avatarPath);
        } else {
          throw new Error('Avatar upload failed or did not return a file path.')
        }
      } catch (uploadError) {
        console.error('Avatar upload failed:', uploadError)
        ElMessage.error(`Avatar upload failed: ${uploadError.message || 'Server error'}`)
        saveLoading.value = false
        return // Stop the save process if upload fails
      }
    }

    // 2. Update profile information (name and potentially new avatar path)
    const updateData = {
      name: editableUserInfo.value.name,
      avatar: avatarPath,
    }

    console.log("Updating profile with data:", updateData);
    await updateProfile(updateData)

    // 3. Success handling
    ElMessage.success('Profile updated successfully!')
    await userStore.getUserInfo() // Refresh user info in store
    isEditing.value = false // Exit edit mode
    // Clear temporary state
    selectedAvatarFile.value = null
    if (avatarPreviewUrl.value) {
      URL.revokeObjectURL(avatarPreviewUrl.value)
      avatarPreviewUrl.value = null
    }

  } catch (error) {
    console.error('Failed to save profile:', error)
    ElMessage.error(`Failed to save profile: ${error.message || 'Server error'}`)
  } finally {
    saveLoading.value = false
  }
}

// Handle cancelling the edit
const handleCancelEdit = () => {
  isEditing.value = false
  // Clear temporary state
  selectedAvatarFile.value = null
  if (avatarPreviewUrl.value) {
    URL.revokeObjectURL(avatarPreviewUrl.value)
    avatarPreviewUrl.value = null
  }
  // Optionally reset editableUserInfo if needed, though entering edit mode does this
  // resetEditableInfo()
}

// Change password dialog
const showChangePasswordDialog = () => {
  changePasswordDialogVisible.value = true
}

// Password change success callback
const handlePasswordChanged = () => {
  ElMessage.success('Password changed successfully')
  loadUserInfo()
}

// Handle export all data
const handleExportAllData = async () => {
  exportLoading.value = true;
  try {
    const response = await exportAllData();
    
    // Console may display XMLHttpRequest errors, but this is a browser dev tool issue
    
    // Check if response is empty
    if (!response) {
      ElMessage.error('Export failed: No data returned from server');
      return;
    }
    
    // Create blob object
    const blob = new Blob([response], { type: 'application/json' });
    
    // Check if there is content
    if (blob.size === 0) {
      ElMessage.warning('No data to export');
      return;
    }
    
    // Read Blob content to check if data is empty
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const jsonData = JSON.parse(e.target.result);
        
        // Check data structure
        if (jsonData && jsonData.musicCount === 0) {
          // Continue download but notify user about no music data
          ElMessage.info('Account data exported successfully, but you have no music data');
        }
        
        // Handle download
        handleDownload(response, `user_${userInfo.value.userid}_all_data.json`);
        ElMessage.success('All data exported successfully');
      } catch (parseError) {
        console.error('Failed to parse response data:', parseError);
        // Still continue with download
        handleDownload(response, `user_${userInfo.value.userid}_all_data.json`);
        ElMessage.success('Data exported successfully');
      }
    };
    
    reader.readAsText(blob);
  } catch (error) {
    console.error('Failed to export all data:', error);
    ElMessage.error(`Export failed: ${error.message || 'Server error'}`);
    
    // Add more debug info
    if (error.response) {
      console.error('Error response status:', error.response.status);
      console.error('Error response content:', error.response.data);
    }
  } finally {
    exportLoading.value = false;
  }
};

// Handle file download
const handleDownload = (response, fileName) => {
  try {
    // Validate response
    if (!response) {
      ElMessage.error('Download failed: Empty response');
      return;
    }
    
    // Ensure fileName has a value
    const safeFileName = fileName || `export_data_${Date.now()}.json`;
    
    // If response is not a blob, convert to blob
    let blob;
    if (response instanceof Blob) {
      blob = response;
    } else {
      // Convert to blob
      blob = new Blob([response], { type: 'application/json' });
    }
    
    // If blob size is 0, may have no data
    if (blob.size === 0) {
      ElMessage.warning('Exported data is empty');
      return;
    }
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', safeFileName);
    
    // Set style to hide link
    link.style.display = 'none';
    
    // Execute download
    document.body.appendChild(link);
    link.click();
    
    // Clean up DOM and URL
    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    }, 100);
    
  } catch (error) {
    console.error('File download processing failed:', error);
    ElMessage.error(`Download failed: ${error.message || 'Unknown error'}`);
  }
};

// Handle delete account
const handleDeleteAccount = async () => {
  try {
    // Confirmation dialogs (existing code)
    await ElMessageBox.confirm(
      'Are you sure you want to delete your account? This cannot be undone and all your personal data and music will be permanently deleted. We recommend exporting your data before deletion.',
      'Delete Account Confirmation',
      {
        confirmButtonText: 'Confirm Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
        distinguishCancelAndClose: true
      }
    );
    await ElMessageBox.confirm(
      'Please confirm again: Do you really want to delete your account? This action is irreversible!',
      'Final Confirmation',
      {
        confirmButtonText: 'Yes, delete my account',
        cancelButtonText: 'Cancel',
        type: 'danger'
      }
    );

    deleteLoading.value = true;

    // Call the backend API to delete the account
    const response = await deleteAccount(); // Assuming this throws on non-200/error code

    // --- Success Handling ---
    // The API call was successful based on the interceptor logic

    ElMessage.success(response?.message || 'Account successfully deleted');

    // Use the store's logoutAction to clear state and redirect
    await userStore.logoutAction();
    // No need to manually push router, logoutAction should handle it.

  } catch (error) {
    // Handle errors (cancellation or actual API errors)
    if (error !== 'cancel' && error !== 'close') {
      console.error('Failed to delete account:', error);
      // Error message display is likely handled by the axios interceptor.
      // We can add specific blob parsing here if the interceptor doesn't handle it well for this case.
      if (error.response && error.response.data instanceof Blob && error.response.data.type === 'application/json') {
          try {
            const errorText = await error.response.data.text();
            const errorJson = JSON.parse(errorText);
            if(errorJson.message) {
                ElMessage.error(errorJson.message); // Show specific message if available
            }
          } catch (e) {
             console.error('Could not parse error blob during account deletion:', e);
          }
       }
    }
  } finally {
    deleteLoading.value = false;
  }
}

// Handle export music files
const handleExportMusicFiles = async () => {
  exportMusicLoading.value = true
  try {
    const response = await exportMusicFiles()

    // The backend now returns JSON with a message if no files exist
    // We need to check the response type and potentially parse JSON
    if (response instanceof Blob) {
      if (response.type === 'application/json') {
        // Try to read the JSON message from the blob
        const reader = new FileReader();
        reader.onload = async (e) => {
          try {
            const jsonData = JSON.parse(e.target.result);
            ElMessage.warning(jsonData.message || 'No music files to export');
          } catch (parseError) {
            console.error('Failed to parse JSON error response:', parseError);
            ElMessage.warning('No music files to export or invalid response.');
          }
        };
        reader.readAsText(response);
      } else if (response.type === 'application/octet-stream' || response.type === 'application/zip') {
        // It's a zip file, proceed with download
        if (response.size === 0) {
          ElMessage.warning('No music files were exported (empty zip).')
        } else {
          const fileName = `music_files_${userInfo.value.userid}.zip`
          handleDownload(response, fileName)
          ElMessage.success('Music files exported successfully')
        }
      } else {
         ElMessage.error('Received unexpected file type for export.');
      }
    } else {
      ElMessage.error('Export failed: Invalid response from server')
    }

  } catch (error) {
    console.error('Failed to export music files:', error)
    // Check if the error object contains a message from the backend JSON response
    let errorMessage = 'Export failed: Server error';
    if (error.response && error.response.data instanceof Blob && error.response.data.type === 'application/json') {
       // Attempt to read the error message from the blob
       try {
         const errorText = await error.response.data.text();
         const errorJson = JSON.parse(errorText);
         errorMessage = errorJson.message || errorMessage;
       } catch (e) {
          console.error('Could not parse error blob', e);
       }
    } else if (error.message) {
        errorMessage = `Export failed: ${error.message}`;
    }
    ElMessage.error(errorMessage);
  } finally {
    exportMusicLoading.value = false
  }
}
</script>

<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <h2>Profile</h2>
          <div>
            <el-button 
              v-if="!isEditing"
              type="primary" 
              :icon="Edit" 
              @click="enterEditMode"
            >
              Edit Profile
            </el-button>
            <el-button 
              type="info" 
              :icon="RefreshRight" 
              @click="loadUserInfo" 
              :loading="loading"
            >
              Refresh
            </el-button>
          </div>
        </div>
      </template>

      <el-skeleton :loading="loading" animated>
        <template #default>
          <el-form :model="editableUserInfo" label-position="top">
            <div class="profile-content">
              <!-- Avatar Section -->
              <div class="profile-avatar-edit">
                <el-avatar 
                  :size="100" 
                  :src="avatarSrc"
                >
                  {{ getDefaultAvatar() }}
                </el-avatar>
                <el-upload
                  v-if="isEditing"
                  class="avatar-uploader"
                  action="#" 
                  :show-file-list="false"
                  :auto-upload="false"
                  accept="image/*"
                  @change="handleAvatarChange"
                >
                  <el-button type="primary" :icon="UploadFilled" circle></el-button>
                  <template #tip>
                    <div class="el-upload__tip text-muted">
                      Click button to change avatar (JPG/PNG/GIF, &lt; 2MB)
                    </div>
                  </template>
                </el-upload>
              </div>

              <!-- Info Section -->
              <div class="profile-info">
                <el-descriptions v-if="!isEditing" title="User Details" :column="1" border>
                  <el-descriptions-item label="User ID">{{ userInfo.userid }}</el-descriptions-item>
                  <el-descriptions-item label="Username">{{ userInfo.name }}</el-descriptions-item>
                  <el-descriptions-item label="Email">{{ userInfo.email }}</el-descriptions-item>
                  <el-descriptions-item label="Role">
                    <el-tag type="success" v-if="userInfo.role === 'ADMIN'">Admin</el-tag>
                    <el-tag v-else>User</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="Status">
                    <el-tag type="success" v-if="userInfo.verificationStatus">Verified</el-tag>
                    <el-tag type="danger" v-else>Unverified</el-tag>
                  </el-descriptions-item>
                </el-descriptions>

                <div v-else> <!-- Editing Form Fields -->
                  <el-form-item label="User ID">
                    <el-input :value="editableUserInfo.userid" disabled />
                  </el-form-item>
                   <el-form-item label="Email">
                    <el-input :value="editableUserInfo.email" disabled />
                  </el-form-item>
                  <el-form-item label="Username" prop="name">
                    <el-input v-model="editableUserInfo.name" placeholder="Enter your username" />
                  </el-form-item>
                  <!-- Role and Status are typically not user-editable -->
                   <el-form-item label="Role">
                     <el-tag type="success" v-if="editableUserInfo.role === 'ADMIN'">Admin</el-tag>
                     <el-tag v-else>User</el-tag>
                  </el-form-item>
                   <el-form-item label="Status">
                      <el-tag type="success" v-if="editableUserInfo.verificationStatus">Verified</el-tag>
                     <el-tag type="danger" v-else>Unverified</el-tag>
                  </el-form-item>

                  <div class="edit-actions">
                    <el-button 
                      type="success" 
                      :icon="Check" 
                      @click="handleSaveProfile" 
                      :loading="saveLoading"
                    >
                      Save Changes
                    </el-button>
                    <el-button 
                      type="info" 
                      :icon="Close" 
                      @click="handleCancelEdit"
                      :disabled="saveLoading"
                    >
                      Cancel
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-form>
        </template>
      </el-skeleton>
    </el-card>

    <el-card class="profile-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <h2>Account Security</h2>
        </div>
      </template>
      
      <div class="security-options">
        <el-space direction="vertical" size="large" fill style="width: 100%;">
          <div class="security-item">
            <div>
              <h3>Change Password</h3>
              <p class="text-muted">Regularly changing your password increases account security</p>
            </div>
            <el-button @click="showChangePasswordDialog">Change Password</el-button>
          </div>
        
        </el-space>
      </div>
    </el-card>
    
    <!-- Data export and account deletion card -->
    <el-card class="profile-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <h2>Data Management</h2>
        </div>
      </template>
      
      <div class="security-options">
        <el-space direction="vertical" size="large" fill style="width: 100%;">
          <!-- Data export option -->
          <div class="security-item">
            <div>
              <h3>Export All Data</h3>
              <p class="text-muted">Export all your account and music data at once</p>
            </div>
            <el-button @click="handleExportAllData" :loading="exportLoading" type="primary">Export All Data</el-button>
          </div>

          <!-- Music file export option -->
          <div class="security-item">
            <div>
              <h3>Export Music Files</h3>
              <p class="text-muted">Download all your music files as a ZIP archive</p>
            </div>
            <el-button @click="handleExportMusicFiles" :loading="exportMusicLoading" type="primary">Export Music Files</el-button>
          </div>
          
          <!-- Account deletion option -->
          <div class="security-item delete-account">
            <div>
              <h3>Delete Account</h3>
              <p class="text-muted danger-text">Delete your account and all related data (this action cannot be undone)</p>
            </div>
            <el-button 
              @click="handleDeleteAccount" 
              :loading="deleteLoading" 
              type="danger"
            >
              Delete Account
            </el-button>
          </div>
        </el-space>
      </div>
    </el-card>

    <!-- Change password dialog -->
    <ChangePasswordDialog 
      v-model:visible="changePasswordDialogVisible"
      @success="handlePasswordChanged"
    />
  </div>
</template>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.profile-card {
  background-color: #1f1f1f;
  border: 1px solid #333;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: #fff;
}

.profile-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.profile-avatar-edit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  margin-bottom: 10px;
  position: relative; /* For positioning the upload button */
}

.avatar-uploader .el-button {
  margin-top: 10px;
}

.avatar-uploader .el-upload__tip {
  font-size: 12px;
  color: #aaa;
  margin-top: 5px;
}

.profile-info {
  width: 100%;
}

.edit-actions {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.security-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #333;
}

.security-item:last-child {
  border-bottom: none;
}

.security-item h3 {
  margin: 0 0 5px 0;
  color: #fff;
}

.text-muted {
  color: #aaa;
  margin: 0;
  font-size: 14px;
}

.danger-text {
  color: #ff6b6b;
}

.delete-account {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #ff6b6b;
}

/* Responsive adjustments */
@media (min-width: 768px) {
  .profile-content {
    flex-direction: row;
    align-items: flex-start;
  }
  
  .profile-avatar-edit {
    margin-right: 30px; /* Increased spacing */
    margin-bottom: 0;
  }
  
  .profile-info {
    flex: 1;
  }
}
</style> 