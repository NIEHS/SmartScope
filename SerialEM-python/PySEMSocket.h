#pragma once
#include <string>

#ifdef _WIN32

// Windows-specific
#include <winsock.h>
#define LONG long
#else

// Linux and Mac variants
#include <sys/socket.h>
#include <arpa/inet.h>
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define SOCKET int
#define SOCKADDR_IN struct sockaddr_in
#define PSOCKADDR struct sockaddr *
#define BOOL int
#define LONG int
#define sprintf_s snprintf
#define vsprintf_s vsnprintf
#define strcpy_s(dst, siz, src) strncpy(dst, src, (siz)); dst[(siz) - 1] = 0x00
#define strncpy_s(dst, siz, src, d) strncpy(dst, src, (siz)); (dst)[(siz) - 1] = 0x00
#endif

// Supported MRC file types/data types
#define MRC_MODE_BYTE          0
#define MRC_MODE_SHORT         1
#define MRC_MODE_FLOAT         2
#define MRC_MODE_USHORT        6
#define MRC_MODE_RGB           16

#define ERR_BUF_SIZE 320
#define MAX_SCRIPT_LANG_ARGS 20

#define B3DMIN(a,b) ((a) < (b) ? (a) : (b))

// Macros for adding arguments
#define LONG_ARG(b) mLongArgs[mNumLongSend++] = b;
#define BOOL_ARG(b) mBoolArgs[mNumBoolSend++] = b;
#define DOUBLE_ARG(b) mDoubleArgs[mNumDblSend++] = b;

enum {PSS_RegularCommand = 1, PSS_ChunkHandshake, PSS_OKtoRunExternalScript,
      PSS_GetBufferImage, PSS_PutImageInbuffer};

// Modified version of the script data structure used in SerialEM
struct ScriptLangData {
  int functionCode;                        // Command code (index) from plugin
  std::string strItems[MAX_SCRIPT_LANG_ARGS];  // String items from plugin (use from 1)
  int itemInt[MAX_SCRIPT_LANG_ARGS];       // Integer value by atoi, from plugin
  double itemDbl[MAX_SCRIPT_LANG_ARGS];    // double value from plugin
  int lastNonEmptyInd;                     // Index of last non-empty item from plugin
  std::string reportedStrs[6];                 // Reported string values after command
  double reportedVals[6];                  // Reported double values after command
  bool repValIsString[6];                  // Flag for whether reported value is string
  int highestReportInd;                    // Index of highest reported value (from 0)
  int errorOccurred;                       // Flag that an error occurred in the command
  int commandReady;                        // Flag set by plugin that command is ready
  bool gotExceptionText;                   // Flag that strItems has exception text
};

// The class
class CPySEMSocket
{
public:
  CPySEMSocket(void);
  ~CPySEMSocket(void);
  char mErrorBuf[ERR_BUF_SIZE];
  ScriptLangData *mScriptData;

private:
  bool mWSAinitialized;
  
  unsigned short mPort;
  char *mIPaddress;
  SOCKET mServer;
  SOCKADDR_IN mSockAddr;
  int mChunkSize;
  int mSuperChunkSize;
  bool mCloseBeforeNextUse;

// Declarations needed on both sides (without array on other side)
// IF A MAX IS CHANGED, PLUGINS BUILT WITH OLDER SIZE WILL NOT LOAD
#define ARGS_BUFFER_CHUNK 1024
#define MAX_LONG_ARGS 16
#define MAX_DBL_ARGS 8
#define MAX_BOOL_ARGS 8

  int mHandshakeCode;
  int mNumLongSend;
  int mNumBoolSend;
  int mNumDblSend;
  int mNumLongRecv;
  int mNumBoolRecv;
  int mNumDblRecv;
  bool mRecvLongArray;
  LONG *mLongArray;
  LONG mLongArgs[MAX_LONG_ARGS];   // Max is 16
  double mDoubleArgs[MAX_DBL_ARGS];  // Max is 8
  BOOL mBoolArgs[MAX_BOOL_ARGS];   // Max is 8
  char *mArgsBuffer;
  int mArgBufSize;
  int mNumBytesSend;

public:
  int InitializeSocket(int port = 0, const char *ipAddress = NULL);
  int ExchangeMessages();
  int OpenServerSocket();
  void CloseServer();
  int ReallocArgsBufIfNeeded(int needSize);

  void InitializePacking(int funcCode);
  void SendAndReceiveArgs();
  int SendOneArgReturnRetVal(int funcCode, int argument);
  const char *GetOneString(int funcCode);
  void AddStringAsLongArray(const char *name, LONG *longArr, int maxLen);
  LONG *AddLongsAndStrings(LONG *longVals, int numLongs, 
                                  const char **strings, int numStrings);
  LONG *AddItemArrays();
  int ReceiveImage(char *imArray, int numBytes, int numChunks);
  int SendImage(void *imArray, int imSize);
  int SendBuffer(char *buffer, int numBytes);
  void ReportErrorAndClose(int retval, const char *message);
  int FinishGettingBuffer(char *buffer, int numReceived, 
                                 int numExpected, int bufSize);
  int FinishSendingBuffer(char *buffer, int numBytes, 
                                 int numTotalSent);
  int UnpackReceivedData(int limitedNum);
  int PackDataToSend();
  void CloseBeforeNextUse();
  void UninitializeWSA(void);

  int RegularCommand(void);
  int OKtoRunExternalScript(BOOL &OKtoRun);
  void *GetBufferImage(int bufInd, int ifFFT, const char *bufStr, int &imType,
                       int &rowBytes, int &sizeX, int &sizeY, int &itemSize,
                       char *format);
  int PutImageInbuffer(void *imArray, int imType, int sizeX, int sizeY, int itemBytes,
                       int toBuf, int baseBuf, int moreBinning, int capFlag);
};
