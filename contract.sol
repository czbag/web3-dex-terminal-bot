// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

// Uniswap V3 Router
interface ISwapRouter02 {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

// Uniswap V2 Router
interface IUniswapV2Router02 {
    function swapExactETHForTokens(
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external payable returns (uint[] memory amounts);

    function swapExactTokensForETH(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint[] memory amounts);

    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint[] memory amounts);
}

interface IWETH9 {
    function deposit() external payable;
    function withdraw(uint256) external;
    function approve(address, uint256) external returns (bool);
    function transfer(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

contract TradingBotSwap is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    ISwapRouter02 public immutable swapRouterV3;
    IUniswapV2Router02 public immutable swapRouterV2;
    IWETH9 public immutable WETH;
    
    event SwapV3(
        address indexed user,
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut
    );
    
    event SwapV2(
        address indexed user,
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut
    );
    
    event ETHWithdrawn(uint256 amount, address indexed to);
    event TokensWithdrawn(address indexed token, uint256 amount, address indexed to);
    
    constructor(
        address _swapRouterV3,
        address _swapRouterV2,
        address _weth
    ) Ownable(msg.sender) ReentrancyGuard() {
        swapRouterV3 = ISwapRouter02(_swapRouterV3);
        swapRouterV2 = IUniswapV2Router02(_swapRouterV2);
        WETH = IWETH9(_weth);
    }
    
    // ========================================================================
    // UNISWAP V3 SWAPS
    // ========================================================================
    
    /**
     * @notice Свап ETH на токен через Uniswap V3
     */
    function swapV3_ETHForToken(
        address tokenOut,
        uint24 fee,
        uint256 amountOutMinimum,
        uint160 sqrtPriceLimitX96
    ) external payable nonReentrant returns (uint256 amountOut) {
        require(msg.value > 0, "Amount must be greater than 0");
        require(tokenOut != address(0), "Invalid token address");
        require(tokenOut != address(WETH), "Cannot swap to WETH");
        
        WETH.deposit{value: msg.value}();
        require(WETH.approve(address(swapRouterV3), msg.value), "Approve failed");
        
        ISwapRouter02.ExactInputSingleParams memory params = ISwapRouter02
            .ExactInputSingleParams({
                tokenIn: address(WETH),
                tokenOut: tokenOut,
                fee: fee,
                recipient: msg.sender,
                amountIn: msg.value,
                amountOutMinimum: amountOutMinimum,
                sqrtPriceLimitX96: sqrtPriceLimitX96
            });
        
        amountOut = swapRouterV3.exactInputSingle(params);
        
        emit SwapV3(msg.sender, address(0), tokenOut, msg.value, amountOut);
        
        return amountOut;
    }
    
    /**
     * @notice Свап токена на ETH через Uniswap V3
     */
    function swapV3_TokenForETH(
        address tokenIn,
        uint256 amountIn,
        uint24 fee,
        uint256 amountOutMinimum,
        uint160 sqrtPriceLimitX96
    ) external nonReentrant returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be greater than 0");
        require(tokenIn != address(0), "Invalid token address");
        
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).forceApprove(address(swapRouterV3), amountIn);
        
        ISwapRouter02.ExactInputSingleParams memory params = ISwapRouter02
            .ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: address(WETH),
                fee: fee,
                recipient: address(this),
                amountIn: amountIn,
                amountOutMinimum: amountOutMinimum,
                sqrtPriceLimitX96: sqrtPriceLimitX96
            });
        
        amountOut = swapRouterV3.exactInputSingle(params);
        
        WETH.withdraw(amountOut);
        (bool success, ) = msg.sender.call{value: amountOut}("");
        require(success, "ETH transfer failed");
        
        emit SwapV3(msg.sender, tokenIn, address(0), amountIn, amountOut);
        
        return amountOut;
    }
    
    /**
     * @notice Свап токена на токен через Uniswap V3
     */
    function swapV3_TokenForToken(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint24 fee,
        uint256 amountOutMinimum,
        uint160 sqrtPriceLimitX96
    ) external nonReentrant returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be greater than 0");
        require(tokenIn != address(0) && tokenOut != address(0), "Invalid token address");
        
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).forceApprove(address(swapRouterV3), amountIn);
        
        ISwapRouter02.ExactInputSingleParams memory params = ISwapRouter02
            .ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: fee,
                recipient: msg.sender,
                amountIn: amountIn,
                amountOutMinimum: amountOutMinimum,
                sqrtPriceLimitX96: sqrtPriceLimitX96
            });
        
        amountOut = swapRouterV3.exactInputSingle(params);
        
        emit SwapV3(msg.sender, tokenIn, tokenOut, amountIn, amountOut);
        
        return amountOut;
    }
    
    // ========================================================================
    // UNISWAP V2 SWAPS
    // ========================================================================
    
    /**
     * @notice Свап ETH на токен через Uniswap V2
     * @param tokenOut Адрес выходного токена
     * @param amountOutMinimum Минимальное количество токенов для получения
     * @param deadline Timestamp после которого транзакция будет отклонена
     */
    function swapV2_ETHForToken(
        address tokenOut,
        uint256 amountOutMinimum,
        uint256 deadline
    ) external payable nonReentrant returns (uint256 amountOut) {
        require(msg.value > 0, "Amount must be greater than 0");
        require(tokenOut != address(0), "Invalid token address");
        require(deadline >= block.timestamp, "Deadline expired");
        
        address[] memory path = new address[](2);
        path[0] = address(WETH);
        path[1] = tokenOut;
        
        uint[] memory amounts = swapRouterV2.swapExactETHForTokens{value: msg.value}(
            amountOutMinimum,
            path,
            msg.sender,
            deadline
        );
        
        amountOut = amounts[amounts.length - 1];
        
        emit SwapV2(msg.sender, address(0), tokenOut, msg.value, amountOut);
        
        return amountOut;
    }
    
    /**
     * @notice Свап токена на ETH через Uniswap V2
     * @param tokenIn Адрес входного токена
     * @param amountIn Количество входных токенов
     * @param amountOutMinimum Минимальное количество ETH для получения
     * @param deadline Timestamp после которого транзакция будет отклонена
     */
    function swapV2_TokenForETH(
        address tokenIn,
        uint256 amountIn,
        uint256 amountOutMinimum,
        uint256 deadline
    ) external nonReentrant returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be greater than 0");
        require(tokenIn != address(0), "Invalid token address");
        require(deadline >= block.timestamp, "Deadline expired");
        
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).forceApprove(address(swapRouterV2), amountIn);
        
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = address(WETH);
        
        uint[] memory amounts = swapRouterV2.swapExactTokensForETH(
            amountIn,
            amountOutMinimum,
            path,
            msg.sender,
            deadline
        );
        
        amountOut = amounts[amounts.length - 1];
        
        emit SwapV2(msg.sender, tokenIn, address(0), amountIn, amountOut);
        
        return amountOut;
    }
    
    /**
     * @notice Свап токена на токен через Uniswap V2
     * @param tokenIn Адрес входного токена
     * @param tokenOut Адрес выходного токена
     * @param amountIn Количество входных токенов
     * @param amountOutMinimum Минимальное количество выходных токенов
     * @param deadline Timestamp после которого транзакция будет отклонена
     */
    function swapV2_TokenForToken(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutMinimum,
        uint256 deadline
    ) external nonReentrant returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be greater than 0");
        require(tokenIn != address(0) && tokenOut != address(0), "Invalid token address");
        require(deadline >= block.timestamp, "Deadline expired");
        
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).forceApprove(address(swapRouterV2), amountIn);
        
        address[] memory path = new address[](2);
        path[0] = tokenIn;
        path[1] = tokenOut;
        
        uint[] memory amounts = swapRouterV2.swapExactTokensForTokens(
            amountIn,
            amountOutMinimum,
            path,
            msg.sender,
            deadline
        );
        
        amountOut = amounts[amounts.length - 1];
        
        emit SwapV2(msg.sender, tokenIn, tokenOut, amountIn, amountOut);
        
        return amountOut;
    }
    
    /**
     * @notice Свап токена на токен через Uniswap V2 с кастомным path
     * @param amountIn Количество входных токенов
     * @param amountOutMinimum Минимальное количество выходных токенов
     * @param path Массив адресов токенов для роутинга (например [tokenA, WETH, tokenB])
     * @param deadline Timestamp после которого транзакция будет отклонена
     */
    function swapV2_TokenForTokenWithPath(
        uint256 amountIn,
        uint256 amountOutMinimum,
        address[] calldata path,
        uint256 deadline
    ) external nonReentrant returns (uint256 amountOut) {
        require(amountIn > 0, "Amount must be greater than 0");
        require(path.length >= 2, "Invalid path");
        require(deadline >= block.timestamp, "Deadline expired");
        
        address tokenIn = path[0];
        address tokenOut = path[path.length - 1];
        
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenIn).forceApprove(address(swapRouterV2), amountIn);
        
        uint[] memory amounts = swapRouterV2.swapExactTokensForTokens(
            amountIn,
            amountOutMinimum,
            path,
            msg.sender,
            deadline
        );
        
        amountOut = amounts[amounts.length - 1];
        
        emit SwapV2(msg.sender, tokenIn, tokenOut, amountIn, amountOut);
        
        return amountOut;
    }
    
    // ========================================================================
    // ADMIN FUNCTIONS
    // ========================================================================
    
    /**
     * @notice Вывод ETH (только владелец)
     */
    function withdrawETH(address payable to) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid address");
        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH balance");
        
        (bool success, ) = to.call{value: balance}("");
        require(success, "ETH transfer failed");
        
        emit ETHWithdrawn(balance, to);
    }
    
    /**
     * @notice Вывод всех токенов (только владелец)
     * @param tokens Массив адресов токенов для вывода
     * @param to Адрес получателя
     */
    function withdrawTokens(address[] calldata tokens, address to) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid address");
        require(tokens.length > 0, "No tokens provided");
        
        for (uint256 i = 0; i < tokens.length; i++) {
            address token = tokens[i];
            require(token != address(0), "Invalid token address");
            
            uint256 balance = IERC20(token).balanceOf(address(this));
            if (balance > 0) {
                IERC20(token).safeTransfer(to, balance);
                emit TokensWithdrawn(token, balance, to);
            }
        }
    }
    
    receive() external payable {}
}
