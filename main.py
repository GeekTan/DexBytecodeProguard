#!/usr/bin/python
# -*- coding: GB2312 -*-

import argparse
import re
import json
import subprocess
import shutil
import os
import logging
import string
import random
import sys
reload(sys)
sys.setdefaultencoding('GB2312')

class Apk_decode_build:

    def __init__(self,apk_input_path=None,apk_dump_dir=None):
        self.apk_input_path=apk_input_path
        self.apk_dump_dir=apk_dump_dir
        self.SmaliList=[]



    def apk_decode(self):
        if self.apk_dump_dir and self.apk_input_path:
            retcode=subprocess.Popen(['apktool.bat','d',self.apk_input_path,'-o',self.apk_dump_dir,'-f','-r'],stdout=subprocess.PIPE).stdout.read()
            if re.search('Exception in thread',retcode)!=None:
                shutil.rmtree(self.apk_dump_dir)
                sys.exit(1)

    def apk_build(self):
        if self.apk_dump_dir:
            retcode=subprocess.Popen(['apktool.bat','b',self.apk_dump_dir],stdout=subprocess.PIPE).stdout.read()
            if re.search('Exception in thread',retcode)!=None:
                shutil.rmtree(self.apk_dump_dir)
                sys.exit(1)

    def SmaliSearch(self):
        for root,dirs, files in os.walk(self.apk_dump_dir):
            for file in files:
                if file.endswith('.smali'):
                    self.SmaliList.append(os.path.join(root,file))



class Smali_Process:

    def __init__(self,SmaliPath,StrlibJson):

        self.SmaliPath=SmaliPath
        self.SmaliBuf=None
        self.SmaliLine=None
        self.StrlibJson=StrlibJson
        self.Strlibdata=None
        self.StrlibdataTmp=None


    def StrlibJson_read(self):
        with open(self.StrlibJson,'rb+') as fp:
            self.Strlibdata=json.load(fp)
            self.StrlibdataTmp=self.Strlibdata

    def Smali_read(self):
        with open(self.SmaliPath,'rb+') as fp:
          self.SmaliBuf=fp.read()

    def Smali_write(self):
        with open(self.SmaliPath,'wb+') as fp:
          fp.write(self.SmaliBuf)

    def Smali_split(self):
        def func(n):
            n=n.strip()
            if len(n)>0 and not n.startswith(r'.line') and not n.startswith(r'.prologue'):
                return n

        self.SmaliLine=map(lambda n:n.strip(),filter(func,re.split('\r\n',self.SmaliBuf)))


    def Smali_group(self):
        self.SmaliBuf=''.join([x+'\r\n' for x in self.SmaliLine])


    def Smali_filter(self):
        filtertuple1=((':try_start',':try_end'),(':sswitch_data','.end sparse-switch') ,(':array','.end array-data'),(':pswitch_data','.end packed-switch') ,('.annotation','.end annotation'),('.param','.end param'))
        filtertuple2=('move-result','move-exception','.catch')
        def Smali_func1(startstr,endstr):
                startline=endline=None
                i=len(self.SmaliLine)-1
                while i>=0:


                    if self.SmaliLine[i].startswith(startstr) and startline==None and endline==None:
                        startline=i
                        i-=1
                        continue
                    if self.SmaliLine[i].startswith(endstr) and startline!=None and endline==None:
                        endline=i

                        self.SmaliLine[endline]=''.join([x+'\r\n' for x in self.SmaliLine[endline:startline+1]])
                        del self.SmaliLine[endline+1:startline+1]
                        i=endline-1
                        startline=endline=None
                        continue
                    i-=1



        def Smali_func2(str):
                i=len(self.SmaliLine)-1
                while i>0:


                    if self.SmaliLine[i].startswith(str):
                        self.SmaliLine[i-1]=''.join(x+'\r\n' for x in self.SmaliLine[i-1:i+1])
                        del self.SmaliLine[i]
                        continue
                    i-=1

        for i in xrange(len(filtertuple2)):
            Smali_func2(filtertuple2[i])

        for i in xrange(len(filtertuple1)):
            Smali_func1(filtertuple1[i][1], filtertuple1[i][0])

    def Smali_method(self):
        methodstartlable='.locals'
        methodendlable='.end method'

        def func(n,lable):
            if self.SmaliLine[n].startswith(lable):
                return n

        def filterfunc(n):
            if n != None:
                return n

        self.methodstarttuple=tuple(filter(filterfunc,[func(i,methodstartlable) for i in xrange(len(self.SmaliLine))]))
        self.methodendtuple=tuple(filter(filterfunc,[func(i,methodendlable) for i in xrange(len(self.SmaliLine))]))
        self.methodnum=len(self.methodstarttuple)



    def random_label(self,num):
        randomstr=list(string.digits+string.ascii_lowercase)
        random.shuffle(randomstr)
        return ':'+''.join(randomstr[:num])

    def Strlib_fix(self,num,regnum):
        def addreg(matched):
            return 'v'+str(int(matched.group('num')[1:])+regnum)
        self.Strlibdata[num]['String']=re.sub('(?P<num>v\d+)',addreg,self.Strlibdata[num]['String'])
        if self.Strlibdata[num][u'Lable']==u'True':
            randomlable=self.random_label(8)
            def addlable(matched):
                return matched.group('num')+randomlable
            self.Strlibdata[num]['String']=re.sub('(?P<num>\:\w+)',addlable,self.Strlibdata[num]['String'])



    def Smali_Lineinsert(self,methodstart,methodend):


        reg_p_list=re.findall('p\d+',''.join(self.SmaliLine[methodstart:methodend+1]))
        reg_p_list.sort(reverse=True)
        if len(reg_p_list)>0:
            reg_p_num=int(reg_p_list[0][1:])
        else:
            reg_p_num=0
        insert_flag=False
        methodreg=int(re.search('\d+',self.SmaliLine[methodstart]).group(0))
        insertreg_max=0
        StrlibLen=len(self.Strlibdata)
        for i in xrange(methodstart,methodend-1,+1):
            num=random.randint(0,StrlibLen-1)

            if methodreg+int(self.Strlibdata[num][u'Register'].decode('utf-8').encode('ascii'))+reg_p_num<16:
                insert_flag=True
                self.Strlibdata=self.StrlibdataTmp
                self.Strlib_fix(num,methodreg)
                self.SmaliLine[i]+='\r\n'+self.Strlibdata[num][u'String'].decode('utf-8').encode('ascii')
                insertreg_max=int(self.Strlibdata[num][u'Register'].decode('utf-8').encode('ascii'))

        if insert_flag:

            self.SmaliLine[methodstart]=re.sub('\d+',str(methodreg+insertreg_max),self.SmaliLine[methodstart],count=1)


    def Smali_Linegoto(self,methodstart,methodend):

        if methodend-methodstart>2:
            label=self.random_label(8)
            self.SmaliLine[methodstart]+='\r\n'+'goto'+label
            for i in xrange(methodstart+1,methodend,+1):
                self.SmaliLine[i]=label+'\r\n'+self.SmaliLine[i]
                if i==methodend-1:
                    break
                label=self.random_label(8)
                self.SmaliLine[i]+='\r\n'+'goto'+label
            SmaliLineTmp=self.SmaliLine[methodstart+1:methodend-1]
            random.shuffle(SmaliLineTmp)
            self.SmaliLine[methodstart+1:methodend-1]=SmaliLineTmp[:]



def main():

    parser=argparse.ArgumentParser(description=u'DEX文件混淆工具V1.0')
    parser.add_argument('-i',dest='apk_input_path',help=u'APK输入路径')
    parser.add_argument('-idir',dest='apk_dump_dir',help=u'APK解压路径')
    parser.add_argument('-mf',dest='mix_file_path',help=u'混淆单文件路径')
    parser.add_argument('-md',dest='mix_dir_path',help=u'混淆单目录路径')
    parser.add_argument('-strlib',dest='strlib_json',help=u'混淆库路径')
    parser.add_argument('-d',dest='apk_decode',action='store_true',help=u'反编译APK')
    parser.add_argument('-b',dest='apk_build',action='store_true',help=u'重构建APK')
    parser.add_argument('-goto',dest='out_of_order',action='store_true',help=u'乱序混淆')
    parser.add_argument('-insert',dest='junk_code',action='store_true',help=u'加花指令')
   
    args=parser.parse_args()
   
    if args.apk_input_path and args.apk_dump_dir and args.apk_decode:
        apk=Apk_decode_build(args.apk_input_path,args.apk_dump_dir)
        apk.apk_decode()

    if args.apk_dump_dir and args.apk_build:
        apk=Apk_decode_build(apk_dump_dir=args.apk_dump_dir)
        apk.apk_build()

    if args.mix_file_path:

        if args.strlib_json:
            Smali=Smali_Process(args.mix_file_path,args.strlib_json)
        else:
            Smali=Smali_Process(args.mix_file_path,os.path.join(os.getcwd(),'StringLib.json'))

        Smali.StrlibJson_read()
        Smali.Smali_read()
        Smali.Smali_split()
        Smali.Smali_filter()
        Smali.Smali_method()
        if args.junk_code:
            for i in xrange(Smali.methodnum):

                Smali.Smali_Lineinsert(Smali.methodstarttuple[i],Smali.methodendtuple[i])

        if args.out_of_order:
            for i in xrange(Smali.methodnum):
                Smali.Smali_Linegoto(Smali.methodstarttuple[i],Smali.methodendtuple[i])

        Smali.Smali_group()
        Smali.Smali_write()

    if args.mix_dir_path:
        apk=Apk_decode_build(apk_dump_dir=args.mix_dir_path)
        apk.SmaliSearch()
        SmaliList=apk.SmaliList
    

        for i in xrange(len(SmaliList)):
            if args.strlib_json:
                Smali=Smali_Process(SmaliList[i],args.strlib_json)
            else:
                Smali=Smali_Process(SmaliList[i],os.path.join(os.getcwd(),'StringLib.json'))


            Smali.StrlibJson_read()
            Smali.Smali_read()
            Smali.Smali_split()
            Smali.Smali_filter()
            Smali.Smali_method()
            if args.junk_code:
                for i in xrange(Smali.methodnum):

                    Smali.Smali_Lineinsert(Smali.methodstarttuple[i],Smali.methodendtuple[i])

            if args.out_of_order:
                for i in xrange(Smali.methodnum):
                    Smali.Smali_Linegoto(Smali.methodstarttuple[i],Smali.methodendtuple[i])

            Smali.Smali_group()
            Smali.Smali_write()




if __name__=='__main__':

   
    main()
    sys.exit(0)
