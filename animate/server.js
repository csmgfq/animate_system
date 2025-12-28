const express = require('express');
const app = express();
const fs = require('fs');
const path = require('path');
// 正确配置 express.json() 中间件，应该在定义路由之前
app.use(express.json());
// 设置允许跨域访问（如果需要）
const cors = require('cors');
app.use(cors());

// 定义一个路由，用于获取数据（原代码中的获取数据接口，这里修改了路径为 /data）
app.get('/data', (req, res) => {
    const filePath = path.join(__dirname, '/yapi.json');
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error reading file');
        } else {
            const jsonData = JSON.parse(data);
            res.send(jsonData);
        }
    });
});
app.post('/updateData', (req, res) => {
    console.log('Received request body:', req.body);
    const updatedData = req.body;
    if (!updatedData) {
        res.status(400).send('No data received');
        return;
    }
    const filePath = path.join(__dirname, '/yapi.json');
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            console.error(err);
            res.status(500).send('Error reading file');
        } else {
            let jsonData = JSON.parse(data);
            const updatedIds = updatedData.map(item => item.id);
            jsonData.data = jsonData.data.map(row => {
                if (updatedIds.includes(row.id)) {
                    const updatedRow = updatedData.find(updated => updated.id === row.id);
                    return { ...row, ...updatedRow };
                }
                return row;
            });
            fs.writeFile(filePath, JSON.stringify(jsonData), 'utf8', (writeErr) => {
                if (writeErr) {
                    console.error(writeErr);
                    res.status(500).send('Error writing file');
                } else {
                    res.send({ success: true });
                }
            });
        }
    });
});

// 新增路由用于更新数据


const port = 3000;
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}/`);
});