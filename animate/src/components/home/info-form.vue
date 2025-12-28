<template>
  <div>
    <el-card class="card-container">
      <!-- 管理员：用户管理 -->
      <template v-if="isAdmin">
        <el-form @submit.prevent="handleQuery">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="queryName"
                  placeholder="请输入用户名"
                  @keypress.enter="handleQuery"
                  size="small"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="1.5">
              <el-button type="primary" size="small" @click="handleQuery">
                <el-icon><Search /></el-icon>搜索
              </el-button>
            </el-col>

            <el-col :span="1.5">
              <el-button type="primary" @click="handleAdd">
                <el-icon><Plus /></el-icon>新增
              </el-button>
            </el-col>

            <el-col :span="1.5">
              <el-button type="danger" :disabled="multiple" @click="handleDelete">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </el-col>
          </el-row>
        </el-form>

        <el-table :data="displayUserData" @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="45"></el-table-column>
          <el-table-column label="编号" prop="id" width="90"></el-table-column>
          <el-table-column label="用户名" prop="username" width="100"></el-table-column>
          <el-table-column label="性别" prop="gender" width="80"></el-table-column>
          <el-table-column label="职业" prop="occupation" width="120"></el-table-column>
          <el-table-column label="生日" prop="birthday" width="150"></el-table-column>
          <el-table-column label="手机号" prop="phone" width="120"></el-table-column>
          <el-table-column label="邮箱" prop="email" width="200"></el-table-column>
          <el-table-column label="账号" prop="account" width="120"></el-table-column>
          <el-table-column label="密码" prop="password" width="200" :formatter="formatPassword"></el-table-column>

          <el-table-column label="操作" width="120">
            <template #default="scope">
              <el-button type="primary" size="small" @click="handleEdit(scope.row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog :title="title" v-model="open" width="600px">
          <el-form ref="form" :model="form" :rules="rules" label-width="80px">
            <el-row>
              <el-col :span="12" v-for="(label, prop) in formLabels" :key="prop">
                <el-form-item :label="label" :prop="prop">
                  <component
                    :is="prop === 'birthday' ? 'el-date-picker' : 'el-input'"
                    v-model="form[prop]"
                    :placeholder="'请输入' + label"
                    value-format="YYYY-MM-DD"
                    type="date"
                    v-if="prop === 'birthday'"
                  />

                  <el-select v-if="prop === 'gender'" v-model="form.gender">
                    <el-option
                      v-for="dict in sexOptions"
                      :key="dict.value"
                      :label="dict.label"
                      :value="dict.value"
                    />
                  </el-select>

                  <el-input
                    v-if="prop !== 'gender' && prop !== 'birthday'"
                    v-model="form[prop]"
                    :placeholder="'请输入' + label"
                    :show-password="prop === 'password'"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
          <template #footer>
            <el-button @click="open = false">取消</el-button>
            <el-button type="primary" @click="formSubmit">确定</el-button>
          </template>
        </el-dialog>

        <!-- 服务器配置 -->
        <el-divider content-position="left">
          <el-icon><Setting /></el-icon> 后端服务器配置
        </el-divider>
        <el-form label-width="100px" style="max-width: 500px;">
          <el-form-item label="协议">
            <el-select v-model="serverConfig.protocol" style="width: 120px;">
              <el-option label="http" value="http" />
              <el-option label="https" value="https" />
            </el-select>
          </el-form-item>
          <el-form-item label="服务器地址">
            <el-input v-model="serverConfig.ip" placeholder="例如: 192.168.1.100 或 frp-box.com" />
          </el-form-item>
          <el-form-item label="端口号">
            <el-input v-model="serverConfig.port" placeholder="例如: 8088" />
          </el-form-item>
          <el-form-item label="当前地址">
            <el-tag type="info">{{ apiBaseUrl || '使用默认代理' }}</el-tag>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="serverSaving" @click="saveServerConfig">
              保存配置
            </el-button>
            <el-text type="info" style="margin-left: 10px;">
              保存后刷新页面生效
            </el-text>
          </el-form-item>
        </el-form>
      </template>

      <!-- 普通用户：个人信息（只操作 /api/users/me） -->
      <template v-else>
        <el-form :model="meForm" label-width="90px" style="max-width: 620px; margin: 0 auto;">
          <el-form-item label="用户名">
            <el-input v-model="meForm.username" placeholder="请输入用户名" />
          </el-form-item>

          <el-form-item label="性别">
            <el-select v-model="meForm.gender" placeholder="请选择性别" style="width: 100%;">
              <el-option v-for="dict in sexOptions" :key="dict.value" :label="dict.label" :value="dict.value" />
            </el-select>
          </el-form-item>

          <el-form-item label="职业">
            <el-input v-model="meForm.occupation" placeholder="请输入职业" />
          </el-form-item>

          <el-form-item label="生日">
            <el-date-picker v-model="meForm.birthday" type="date" value-format="YYYY-MM-DD" placeholder="请选择生日" style="width: 100%;" />
          </el-form-item>

          <el-form-item label="手机号">
            <el-input v-model="meForm.phone" placeholder="请输入手机号" />
          </el-form-item>

          <el-form-item label="邮箱">
            <el-input v-model="meForm.email" placeholder="请输入邮箱" />
          </el-form-item>

          <el-form-item label="账号">
            <el-input v-model="meForm.account" placeholder="请输入账号" />
          </el-form-item>

          <el-form-item label="新密码">
            <el-input v-model="meForm.password" placeholder="不修改请留空" show-password />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="meSaving" @click="saveMe">保存</el-button>
          </el-form-item>
        </el-form>
      </template>
    </el-card>
  </div>
</template>

<script>
import { Search, Plus, Edit, Delete, Setting } from "@element-plus/icons-vue";
import axios from "axios";
import { getApiBaseUrl, getCustomServerConfig, setCustomServerConfig } from "../../api/baseUrl";

export default {
  components: {
    Search,
    Plus,
    Edit,
    Delete,
    Setting,
  },
  data() {
    return {
      apiBaseUrl: getApiBaseUrl(),
      serverConfig: {
        protocol: 'http',
        ip: '',
        port: '',
      },
      serverSaving: false,
      UserData: [],
      displayUserData: [],
      currentUser: null,
      isAdmin: false,
      meForm: {
        username: "",
        gender: "",
        occupation: "",
        birthday: "",
        phone: "",
        email: "",
        account: "",
        password: "",
      },
      meSaving: false,
      title: "",
      open: false,
      single: true,
      multiple: true,
      queryName: "",
      form: {},
      sexOptions: [
        { value: "男", label: "男" },
        { value: "女", label: "女" },
        { value: "未知", label: "未知" },
      ],
      selectedRows: [],
      rules: {
        username: [
          { required: true, message: "用户名称不能为空", trigger: "blur" },
        ],
        occupation: [
          { required: true, message: "职业不能为空", trigger: "blur" },
        ],
        email: [
          { required: true, message: "邮箱地址不能为空", trigger: "blur" },
          {
            type: "email",
            message: "'请输入正确的邮箱地址",
            trigger: ["blur", "change"],
          },
        ],
        account: [{ required: true, message: "账号不能为空", trigger: "blur" }],
        password: [
          { required: true, message: "用户密码不能为空", trigger: "blur" },
        ],
        phone: [
          { required: true, message: "手机号码不能为空", trigger: "blur" },
          {
            pattern: /^1[3-9]\d{9}$/,
            message: "请输入正确的手机号码",
            trigger: "blur",
          },
        ],
      },
      formLabels: {
        id: "用户ID",
        username: "用户名",
        gender: "性别",
        occupation: "职业",
        birthday: "生日",
        phone: "手机号码",
        email: "邮箱地址",
        account: "账号",
        password: "用户密码",
      },
    };
  },
  created() {
    // 初始化服务器配置
    const customConfig = getCustomServerConfig();
    if (customConfig) {
      this.serverConfig.protocol = customConfig.protocol || 'http';
      this.serverConfig.ip = customConfig.ip || '';
      this.serverConfig.port = customConfig.port || '';
    }

    try {
      const raw = localStorage.getItem('currentUser')
      if (raw) {
        this.currentUser = JSON.parse(raw)
        this.isAdmin = !!this.currentUser?.is_admin
      }
    } catch (e) {
      this.currentUser = null
      this.isAdmin = false
    }
    if (this.isAdmin) {
      this.fetchUserData();
    } else {
      this.fetchMe();
    }
  },
  methods: {
    saveServerConfig() {
      this.serverSaving = true;
      const protocol = (this.serverConfig.protocol || 'http').trim();
      const ip = (this.serverConfig.ip || '').trim();
      const port = (this.serverConfig.port || '').trim();

      if (ip && port) {
        setCustomServerConfig(ip, port, protocol);
        this.apiBaseUrl = getApiBaseUrl();
        this.$message.success('服务器配置已保存，刷新页面后生效');
      } else if (!ip && !port) {
        setCustomServerConfig(null, null);
        this.apiBaseUrl = getApiBaseUrl();
        this.$message.success('已清除自定义服务器配置');
      } else {
        this.$message.warning('请同时填写服务器地址和端口号');
      }
      this.serverSaving = false;
    },

    fetchMe() {
      axios
        .get(`${this.apiBaseUrl}/api/users/me`)
        .then((resp) => {
          const user = resp?.data?.data?.user
          if (user) {
            this.meForm = {
              username: user.username || "",
              gender: user.gender || "",
              occupation: user.occupation || "",
              birthday: user.birthday || "",
              phone: user.phone || "",
              email: user.email || "",
              account: user.account || "",
              password: "",
            }
          }
        })
        .catch((e) => {
          console.error(e)
          this.$message.error("无法获取个人信息，请先登录")
        })
    },

    saveMe() {
      this.meSaving = true
      const payload = { ...this.meForm }
      if (!payload.password) {
        delete payload.password
      }
      axios
        .put(`${this.apiBaseUrl}/api/users/me`, payload)
        .then((resp) => {
          const user = resp?.data?.data?.user
          if (user) {
            localStorage.setItem('currentUser', JSON.stringify(user))
            this.currentUser = user
          }
          this.meForm.password = ""
          this.$message.success("保存成功")
        })
        .catch((e) => {
          console.error(e)
          const msg = e?.response?.data?.msg || e?.response?.data?.message || "保存失败"
          this.$message.error(msg)
        })
        .finally(() => {
          this.meSaving = false
        })
    },

    fetchUserData() {
      if (!this.isAdmin) {
        this.UserData = []
        this.displayUserData = []
        return
      }
      axios
        .get(`${this.apiBaseUrl}/api/users/info`)
        .then((response) => {
          this.UserData = response?.data?.data || [];
          this.displayUserData = [...this.UserData]
        })
        .catch((error) => {
          console.error("There was an error fetching the data!", error);
          // 显示用户友好的错误消息
          this.$message.error("无法获取用户数据，请稍后重试。");
        });
    },
    handleQuery() {
      const q = (this.queryName || '').trim()
      if (q) {
        this.displayUserData = (this.UserData || []).filter(
          (item) => item?.username && String(item.username).includes(q)
        );
      } else {
        this.displayUserData = [...(this.UserData || [])]
      }
      this.queryName = "";
    },
    handleSelectionChange(selection) {
      this.selectedRows = selection;
      this.single = selection.length !== 1;
      this.multiple = selection.length === 0;
    },
    handleAdd() {
      this.form = {};
      this.title = "新增用户信息";
      this.open = true;
    },

    handleEdit(row) {
      this.form = { ...row };
      this.title = "编辑用户信息";
      this.open = true;
    },

    handleDelete() {
      this.$confirm("确定删除选中的用户吗?", "提示", { type: "warning" })
        .then(() => {
          const idsToDelete = this.selectedRows.map((row) => row.id);
          if (!idsToDelete.length) return;
          axios
            .delete(`${this.apiBaseUrl}/api/users/${idsToDelete.join(',')}`)
            .then(() => this.fetchUserData())
            .catch(console.error);
        })
        .catch(() => {});
    },

    formSubmit() {
      if (!this.isAdmin) return;
      const payload = { ...this.form };
      // 后端字段为 username，而不是 name
      if (payload.name && !payload.username) {
        payload.username = payload.name;
        delete payload.name;
      }

      const req = payload.id
        ? axios.put(`${this.apiBaseUrl}/api/users/${payload.id}`, payload)
        : axios.post(`${this.apiBaseUrl}/api/users`, payload);

      req
        .then(() => {
          this.open = false;
          this.fetchUserData();
        })
        .catch((e) => {
          console.error(e);
          this.$message.error("操作失败，请稍后重试");
        });
    },

    formatPassword(row, column) {
      return '****';
    },
  },
};
</script>
