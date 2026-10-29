const {build}=require('./package.json');
const {signExecutable,...win}=build.win;
module.exports={...build,win,forceCodeSigning:true};
